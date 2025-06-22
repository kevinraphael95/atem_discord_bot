# ────────────────────────────────────────────────────────────────────────────────
# 🧠 TestQuestion.py — Commande !testquestion
# Objectif : Deviner une carte Yu-Gi-Oh à partir de sa description parmi 4 choix
# Variante : les mauvaises réponses viennent du même archétype si applicable
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
# 📦 IMPORTS
# ────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import random
import asyncio
import re
from supabase_client import supabase

REACTIONS = ["🇦", "🇧", "🇨", "🇩"]


# ────────────────────────────────────────────────────────────────
# 🧹 Filtrage de cartes interdites
# ────────────────────────────────────────────────────────────────
def is_clean_card(card):
    banned_keywords = [
        "@Ignister", "abc -", "abc-", "abyss", "altergeist", "beetrouper", "branded", "cloudian",
        "crusadia", "cyber", "D.D.", "dark world",
        "dragonmaid", "dragon ruler", "dragunity", "exosister", "eyes of blue", "f.a", "f.a.",
        "floowandereeze", "fur hire", "harpie",
        "hero", "hurricail", "infinitrack", "kaiser", "kozaky", "labrynth", "live☆twin", "lunar light", "madolche", "marincess",
        "Mekk-Knight", "metalfoes", "naturia", "noble knight", "number", "numero", "numéro",
        "oni", "Performapal", "phantasm spiral", "pot", "prophecy", "psychic", "punk", "rescue", "rose dragon",
        "salamangreat", "sky striker", "tierra", "tri-brigade", "unchained"
    ]
    name = card.get("name", "").lower()
    return all(keyword not in name for keyword in banned_keywords)


# ────────────────────────────────────────────────────────────────
# 🧩 CLASSE DU COG
# ────────────────────────────────────────────────────────────────
class TestQuestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}

    async def fetch_card_sample(self, limit=100):
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return random.sample(data.get("data", []), min(limit, len(data.get("data", []))))

    def censor_card_name(self, desc: str, name: str) -> str:
        return re.sub(re.escape(name), "[cette carte]", desc, flags=re.IGNORECASE)

    async def update_streak(self, user_id: str, correct: bool):
        data = supabase.table("ygo_streaks").select("*").eq("user_id", user_id).execute()
        row = data.data[0] if data.data else None

        if row:
            current = row["current_streak"]
            best = row.get("best_streak", 0)
            new_streak = current + 1 if correct else 0
            update_data = {"current_streak": new_streak}
            if correct and new_streak > best:
                update_data["best_streak"] = new_streak
            supabase.table("ygo_streaks").update(update_data).eq("user_id", user_id).execute()
        else:
            supabase.table("ygo_streaks").insert({
                "user_id": user_id,
                "current_streak": 1 if correct else 0,
                "best_streak": 1 if correct else 0
            }).execute()

    @commands.command(
        name="testquestion",
        aliases=["tq"],
        help="🧠 Devine une carte Yu-Gi-Oh à partir de sa description. Multijoueur pendant 60 secondes !"
    )
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def testquestion(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else None

        if guild_id in self.active_sessions and self.active_sessions[guild_id]:
            await self.active_sessions[guild_id].reply("⚠️ Une partie est déjà en cours dans ce serveur.", mention_author=False)
            return

        self.active_sessions[guild_id] = None

        sample = await self.fetch_card_sample(60)
        main_card = None
        archetype_data = None

        for card in sample:
            if "name" not in card or "desc" not in card:
                continue
            archetype = card.get("archetype")
            if archetype:
                url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if len(data.get("data", [])) >= 11:
                                main_card = card
                                archetype_data = data.get("data", [])
                                break
            else:
                main_card = card
                break

        if not main_card:
            await ctx.send("❌ Impossible de trouver une carte principale valide.")
            self.active_sessions[guild_id] = None
            return

        main_name = main_card["name"]
        desc = self.censor_card_name(main_card.get("desc", ""), main_name)
        options = [main_card]

        if archetype_data:
            pool = [c for c in archetype_data if c["name"] != main_name and "desc" in c]
        else:
            pool = [c for c in sample if c["name"] != main_name and "desc" in c and is_clean_card(c)]

        pool = random.sample(pool, min(3, len(pool)))
        options += pool
        random.shuffle(options)

        embed = discord.Embed(
            title="🧠 Quelle est cette carte Yu-Gi-Oh ?",
            description=f"```{desc}```\n\n" + "\n".join(f"{REACTIONS[i]} {card['name']}" for i, card in enumerate(options)),
            color=0x3498db
        )
        embed.set_footer(text="Réagissez avec 🇦 🇧 🇨 🇩 — 60 secondes pour répondre !")

        msg = await ctx.send(embed=embed)
        self.active_sessions[guild_id] = msg

        for i in range(len(options)):
            await msg.add_reaction(REACTIONS[i])

        await asyncio.sleep(60)

        msg = await ctx.channel.fetch_message(msg.id)
        results = {REACTIONS[i]: [] for i in range(4)}
        for reaction in msg.reactions:
            if reaction.emoji in REACTIONS:
                async for user in reaction.users():
                    if user.bot:
                        continue
                    if user.id not in [u.id for u in results[reaction.emoji]]:
                        results[reaction.emoji].append(user)

        correct_index = options.index(main_card)
        correct_emoji = REACTIONS[correct_index]
        winners = results[correct_emoji]

        if winners:
            for user in winners:
                await self.update_streak(str(user.id), correct=True)
            winner_mentions = ", ".join(user.mention for user in winners)
            await ctx.send(f"✅ La bonne réponse était **{main_name}** ! Bravo à {winner_mentions} !")
        else:
            await ctx.send(f"❌ La bonne réponse était **{main_name}** ! Personne n’a trouvé...")

        for i, card in enumerate(options):
            await ctx.send(f"{REACTIONS[i]} → {card['name']}")

        self.active_sessions[guild_id] = None


# ────────────────────────────────────────────────────────────────
# 🔌 SETUP DU COG
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestQuestion(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"  # 📚 Pour l’organisation des commandes
    await bot.add_cog(cog)
