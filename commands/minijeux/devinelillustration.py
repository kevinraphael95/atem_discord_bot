# ────────────────────────────────────────────────────────────────────────────────
# 📌 illustration.py — Commande interactive !illustration
# Objectif : Jeu pour deviner une carte Yu-Gi-Oh! à partir de son image croppée.
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import random
import asyncio
import traceback

from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_edit, safe_respond  

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — IllustrationCommand
# ────────────────────────────────────────────────────────────────────────────────
class IllustrationCommand(commands.Cog):
    """
    Commande /illustration et !illustration — Jeu où tout le monde peut répondre à un quiz d’image Yu-Gi-Oh!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonctions utilitaires
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_all_cards(self):
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        return data.get("data", [])

    async def get_similar_cards(self, all_cards, true_card):
        archetype = true_card.get("archetype")
        card_type = true_card.get("type", "")
        if archetype:
            group = [
                c for c in all_cards
                if c.get("archetype") == archetype and c["name"] != true_card["name"]
            ]
        else:
            group = [
                c for c in all_cards
                if c.get("type") == card_type
                and not c.get("archetype")
                and c["name"] != true_card["name"]
            ]
        return random.sample(group, k=min(3, len(group))) if group else []

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Quiz avec boutons
    # ────────────────────────────────────────────────────────────────────────────
    class QuizView(View):
        def __init__(self, bot, choices, correct_idx):
            super().__init__(timeout=60)  # ⏳ 1 minute
            self.bot = bot
            self.choices = choices
            self.correct_idx = correct_idx
            self.answers = {}  # user_id: choix
            for i, choice in enumerate(choices):
                self.add_item(IllustrationCommand.QuizButton(label=choice, idx=i, parent_view=self))

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            if hasattr(self, "message"):
                await safe_edit(self.message, view=self)

    class QuizButton(Button):
        def __init__(self, label, idx, parent_view):
            super().__init__(label=label, style=discord.ButtonStyle.primary)
            self.parent_view = parent_view
            self.idx = idx

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id not in self.parent_view.answers:
                self.parent_view.answers[interaction.user.id] = self.idx
            await interaction.response.send_message(f"✅ Réponse enregistrée : **{self.label}**", ephemeral=True)

    async def start_quiz(self, channel: discord.abc.Messageable):
        """Lance le quiz dans le channel avec boutons."""
        try:
            all_cards = await self.fetch_all_cards()
            if not all_cards:
                return await safe_send(channel, "🚨 Impossible de récupérer les cartes depuis l’API.")

            candidates = [
                c for c in all_cards
                if "image_url_cropped" in c.get("card_images", [{}])[0]
            ]
            if not candidates:
                return await safe_send(channel, "🚫 Pas de cartes avec images croppées.")

            true_card = random.choice(candidates)
            image_url = true_card["card_images"][0].get("image_url_cropped")
            if not image_url:
                return await safe_send(channel, "🚫 Carte sans image croppée.")

            similar = await self.get_similar_cards(all_cards, true_card)
            if len(similar) < 3:
                return await safe_send(channel, "❌ Pas assez de cartes similaires.")

            choices = [true_card["name"]] + [c["name"] for c in similar]
            random.shuffle(choices)
            correct_idx = choices.index(true_card["name"])

            embed = discord.Embed(
                title="🖼️ Devine la carte !",
                color=discord.Color.purple()
            )
            embed.set_image(url=image_url)
            embed.set_footer(text=f"🔹 Archétype : ||{true_card.get('archetype','Aucun')}||")

            view = self.QuizView(self.bot, choices, correct_idx)
            view.message = await safe_send(channel, embed=embed, view=view)

            # attente de fin du quiz
            await view.wait()

            # Mise à jour des streaks Supabase
            for uid, choice in view.answers.items():
                resp = supabase.table("ygo_streaks")\
                    .select("illu_streak,best_illustreak")\
                    .eq("user_id", uid).execute()
                data = resp.data or []
                cur, best = (data[0].get("illu_streak",0), data[0].get("best_illustreak",0)) if data else (0,0)
                if choice == correct_idx:
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 0
                supabase.table("ygo_streaks").upsert({
                    "user_id": uid,
                    "illu_streak": cur,
                    "best_illustreak": best
                }).execute()

            winners = [u for u, idx in view.answers.items() if idx == correct_idx]
            mentions = ", ".join(self.bot.get_user(u).mention for u in winners if self.bot.get_user(u))
            result = f"🎉 Bravo à : {mentions}" if mentions else "Personne n’a trouvé la bonne réponse."

            scores = []
            for uid in view.answers:
                r = supabase.table("ygo_streaks")\
                    .select("illu_streak,best_illustreak")\
                    .eq("user_id", uid).execute().data or []
                cur, best = (r[0]["illu_streak"], r[0]["best_illustreak"]) if r else (0,0)
                scores.append((uid, cur, best))
            scores.sort(key=lambda x: x[1], reverse=True)
            board = "\n".join(
                f"#{i+1} **{self.bot.get_user(uid)}** — Série: `{cur}`, Meilleure: `{best}`"
                for i, (uid, cur, best) in enumerate(scores)
            ) or "Aucun score."

            await safe_send(
                channel,
                f"⏳ Temps écoulé ! La bonne réponse était **{true_card['name']}**.\n"
                f"{result}\n\n**Classement :**\n{board}"
            )

        except Exception as e:
            traceback.print_exc()
            await safe_send(channel, f"❌ Une erreur est survenue : {e}")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="illustration",
        description="🖼️ Devine une carte Yu-Gi-Oh! à partir de son illustration."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.user.id))
    async def slash_illustration(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            await self.start_quiz(interaction.channel)
            await interaction.delete_original_response()
        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="illustration", aliases=["i", "devinelillustration","di"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_illustration(self, ctx: commands.Context):
        try:
            await self.start_quiz(ctx.channel)
        except commands.CommandOnCooldown as e:
            await safe_send(ctx.channel, f"⏳ Attends encore {e.retry_after:.1f}s.")
        except Exception as e:
            traceback.print_exc()
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = IllustrationCommand(bot)
    for cmd in cog.get_commands():
        if not hasattr(cmd, "category"):
            cmd.category = "Minijeux"
    await bot.add_cog(cog)
