# ────────────────────────────────────────────────────────────────────────────────
# 📌 illustration.py — Commande interactive !illustration
# Objectif : Jeu pour deviner une carte Yu-Gi-Oh! à partir de son image croppée.
# Catégorie : Minijeux
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View
import aiohttp
import random
import asyncio
import urllib.parse
import traceback

from supabase_client import supabase
from utils.discord_utils import safe_send, safe_edit  # ✅ Protection 429

# ────────────────────────────────────────────────────────────────────────────────
# 🔤 CONSTANTES
# ────────────────────────────────────────────────────────────────────────────────
REACTIONS = ["🇦", "🇧", "🇨", "🇩"]

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — IllustrationCommand
# ────────────────────────────────────────────────────────────────────────────────
class IllustrationCommand(commands.Cog):
    """
    Commande !illustration — Jeu où tout le monde peut répondre à un quiz d’image Yu-Gi-Oh!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

    @commands.command(
        name="devinelillustration",
        aliases=["di"],
        help="🖼️ Devine une carte Yu-Gi-Oh! à partir de son illustration. (multijoueur)",
        description="Affiche un quiz interactif à partir d’une image croppée de carte."
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def illustration(self, ctx: commands.Context):
        """Commande principale avec quiz d'image et réponses via réactions."""
        try:
            all_cards = await self.fetch_all_cards()
            if not all_cards:
                return await safe_send(ctx.channel, "🚨 Impossible de récupérer les cartes depuis l’API.")

            candidates = [
                c for c in all_cards
                if "image_url_cropped" in c.get("card_images", [{}])[0]
            ]
            if not candidates:
                return await safe_send(ctx.channel, "🚫 Pas de cartes avec images croppées.")

            true_card = random.choice(candidates)
            image_url = true_card["card_images"][0].get("image_url_cropped")
            if not image_url:
                return await safe_send(ctx.channel, "🚫 Carte sans image croppée.")

            similar = await self.get_similar_cards(all_cards, true_card)
            if len(similar) < 3:
                return await safe_send(ctx.channel, "❌ Pas assez de cartes similaires.")

            choices = [true_card["name"]] + [c["name"] for c in similar]
            random.shuffle(choices)
            correct_idx = choices.index(true_card["name"])

            embed = discord.Embed(
                title="🖼️ Devine la carte !",
                description="\n".join(f"{REACTIONS[i]} {n}" for i, n in enumerate(choices)),
                color=discord.Color.purple()
            )
            embed.set_image(url=image_url)
            embed.set_footer(text=f"🔹 Archétype : ||{true_card.get('archetype','Aucun')}||")

            quiz_msg = await safe_send(ctx.channel, embed=embed)

            for emoji in REACTIONS[:len(choices)]:
                await quiz_msg.add_reaction(emoji)

            def check(reaction, user):
                return (
                    reaction.message.id == quiz_msg.id
                    and str(reaction.emoji) in REACTIONS
                    and not user.bot
                )

            answers = {}
            start = asyncio.get_event_loop().time()
            while True:
                timeout = 10 - (asyncio.get_event_loop().time() - start)
                if timeout <= 0:
                    break
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=timeout, check=check)
                except asyncio.TimeoutError:
                    break
                if user.id not in answers:
                    answers[user.id] = REACTIONS.index(str(reaction.emoji))

            await asyncio.sleep(1)

            # Mise à jour des streaks Supabase
            for uid, choice in answers.items():
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

            # Construction du résultat
            winners = [u for u, idx in answers.items() if idx == correct_idx]
            mentions = ", ".join(self.bot.get_user(u).mention for u in winners if self.bot.get_user(u))
            result = f"🎉 Bravo à : {mentions}" if mentions else "Personne n’a trouvé la bonne réponse."

            # Classement
            scores = []
            for uid in answers:
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
                ctx.channel,
                f"⏳ Temps écoulé ! La bonne réponse était **{true_card['name']}**.\n"
                f"{result}\n\n**Classement :**\n{board}"
            )

        except Exception as e:
            traceback.print_exc()
            await safe_send(ctx.channel, f"❌ Une erreur est survenue : {e}")

    
# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = IllustrationCommand(bot)
    for cmd in cog.get_commands():
        if not hasattr(cmd, "category"):
            cmd.category = "Minijeux"
    await bot.add_cog(cog)
