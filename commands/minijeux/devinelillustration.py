# ────────────────────────────────────────────────────────────────────────────────
# 📌 illustration.py — Commande interactive !illustration
# Objectif : Jeu pour deviner une carte Yu-Gi-Oh! à partir de son image croppée
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import random
import asyncio
import traceback

from utils.discord_utils import safe_send, safe_edit
from utils.supabase_client import supabase
from utils.vaact_utils import add_exp_for_streak

# ────────────────────────────────────────────────────────────────────────────────
# 🔒 Empêcher l'utilisation en MP
# ────────────────────────────────────────────────────────────────────────────────
def no_dm():
    async def predicate(ctx):
        if ctx.guild is None:
            await safe_send(ctx, "❌ Cette commande ne peut pas être utilisée en MP.")
            return False
        return True
    return commands.check(predicate)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — IllustrationCommand
# ────────────────────────────────────────────────────────────────────────────────
class IllustrationCommand(commands.Cog):
    """Commande /illustration et !illustration — Devine une carte Yu-Gi-Oh! à partir de son illustration."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_sessions = {}  # guild_id → quiz en cours

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonctions utilitaires
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_all_cards(self):
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
        session = self.bot.aiohttp_session

        if session is None or session.closed:
            return []

        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
            return data.get("data", [])
        except Exception as e:
            print(f"[fetch_all_cards ERROR] {e}")
            return []

    async def get_similar_cards(self, all_cards, true_card):
        archetype = true_card.get("archetype")
        card_type = true_card.get("type", "")
        if archetype:
            group = [
                c for c in all_cards
                if c.get("archetype") == archetype
                and c["name"] != true_card["name"]
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
    # 🔹 Lancer le quiz
    # ────────────────────────────────────────────────────────────────────────────
    async def start_quiz(self, channel: discord.abc.Messageable):
        guild_id = getattr(channel, "guild", None).id if hasattr(channel, "guild") else None
        if guild_id and self.active_sessions.get(guild_id):
            return await safe_send(channel, "⚠️ Un quiz est déjà en cours.")
        if guild_id:
            self.active_sessions[guild_id] = True

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
            embed.set_footer(
                text=f"🔹 Archétype : ||{true_card.get('archetype','Aucun')}||"
            )

            view = self.QuizView(self.bot, choices, correct_idx)
            view.message = await safe_send(channel, embed=embed, view=view)
            await view.wait()

            winners = [
                self.bot.get_user(uid)
                for uid, idx in view.answers.items()
                if idx == correct_idx
            ]

            result_embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=(
                    f"✅ Réponse : **{true_card['name']}**\n"
                    + (
                        f"🎉 Gagnants : {', '.join(w.mention for w in winners if w)}"
                        if winners else "😢 Personne n'a trouvé..."
                    )
                ),
                color=discord.Color.green() if winners else discord.Color.red()
            )
            await safe_send(channel, embed=result_embed)

        except Exception as e:
            traceback.print_exc()
            await safe_send(channel, f"❌ Une erreur est survenue : {e}")
        finally:
            if guild_id:
                self.active_sessions[guild_id] = None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 View et Button pour le quiz
    # ────────────────────────────────────────────────────────────────────────────
    class QuizView(View):
        def __init__(self, bot, choices, correct_idx):
            super().__init__(timeout=60)
            self.bot = bot
            self.choices = choices
            self.correct_idx = correct_idx
            self.answers = {}
            for i, choice in enumerate(choices):
                self.add_item(
                    IllustrationCommand.QuizButton(
                        label=choice,
                        idx=i,
                        parent_view=self
                    )
                )

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
            await interaction.response.send_message(
                f"✅ Réponse enregistrée : **{self.label}**",
                ephemeral=True
            )

    # ────────────────────────────────────────────────────────────────────────────
    # 💬 Commande principale
    # ────────────────────────────────────────────────────────────────────────────
    @commands.group(
        name="devinelillustration",
        aliases=["dli","di","illustration","i"],
        invoke_without_command=True
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @no_dm()
    async def illustration_group(self, ctx: commands.Context):
        await self.start_quiz(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = IllustrationCommand(bot)
    for command in cog.get_commands():
        command.category = "Minijeux"
    await bot.add_cog(cog)
