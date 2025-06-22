# ────────────────────────────────────────────────────────────────
# 🧠 Question.py — Commande !question
# Objectif : Deviner une carte Yu-Gi-Oh à partir de sa description parmi 4 choix
# Bonus : suivi de série de bonnes réponses (streak) enregistré via Supabase
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
# 📦 IMPORTS
# ────────────────────────────────────────────────────────────────
import discord                               # 📘 API Discord
from discord.ext import commands            # 🛠️ Extensions pour commandes
import aiohttp                               # 🌐 Requêtes HTTP asynchrones
import random                                # 🎲 Choix aléatoires
import asyncio                               # ⏳ Timeout & délais
import re                                    # ✂️ Remplacement avec RegEx
from supabase_client import supabase         # ☁️ Base de données Supabase

# Réactions pour les 4 propositions
REACTIONS = ["🇦", "🇧", "🇨", "🇩"]

# ────────────────────────────────────────────────────────────────
# 🧹 Filtrage de cartes interdites (anti-meta, anti-spam, etc.)
# ────────────────────────────────────────────────────────────────
def is_clean_card(card):
    banned_keywords = [
        "@Ignister", "abc -", "abc-", "abyss", "altergeist", "beetrouper", "branded", "cloudian", 
        "crusadia", "cyber", "D.D.", "dark world", "dragonmaid", "dragon ruler", "dragunity",
        "exosister", "eyes of blue", "f.a", "f.a.", "floowandereeze", "fur hire", "harpie", 
        "hero", "hurricail", "infinitrack", "kaiser", "kozaky", "labrynth", "live☆twin", "lunar light", 
        "madolche", "marincess", "Mekk-Knight", "metalfoes", "naturia", "noble knight", "number", 
        "numero", "numéro", "oni", "Performapal", "phantasm spiral", "pot", "prophecy", "psychic", 
        "punk", "rescue", "rose dragon", "salamangreat", "sky striker", "tierra", "tri-brigade", "unchained"
    ]
    name = card.get("name", "").lower()
    return all(keyword not in name for keyword in banned_keywords)

# ────────────────────────────────────────────────────────────────
# GET VALID CARD (avec archétype valide si possible)
# ────────────────────────────────────────────────────────────────
async def get_valid_card(sample, min_count=11):
    archetype_cache = {}
    max_attempts = 30
    attempts = 0

    while attempts < max_attempts:
        card = random.choice(sample)
        attempts += 1

        archetype = card.get("archetype")
        if not archetype:
            return card

        if archetype not in archetype_cache:
            url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        archetype_cache[archetype] = len(data.get("data", []))
                    else:
                        archetype_cache[archetype] = 0

        if archetype_cache[archetype] >= min_count:
            return card

    return None

# ────────────────────────────────────────────────────────────────
# 🧩 CLASSE DU COG
# ────────────────────────────────────────────────────────────────
class Question(commands.Cog):
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

    @commands.command(name="question", aliases=["q"], help="🧠 Devine une carte Yu-Gi-Oh à partir de sa description !")
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def question(self, ctx):
        sample = await self.fetch_card_sample(limit=60)
        main_card = await get_valid_card(sample, min_count=11)

        if not main_card:
            await ctx.send("❌ Aucune carte valide trouvée.")
            return

        guild_id = ctx.guild.id if ctx.guild else None
        if guild_id in self.active_sessions and self.active_sessions[guild_id]:
            await self.active_sessions[guild_id].reply(
                "⚠️ Une partie est déjà en cours dans ce serveur. Patientez qu'elle se termine.",
                mention_author=False
            )
            return

        self.active_sessions[guild_id] = None

        archetype = main_card.get("archetype")
        false_cards_pool = []
        if archetype:
            url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        archetype_cards = data.get("data", [])
                        filtered = [c for c in archetype_cards if c["name"] != main_card["name"] and is_clean_card(c)]
                        if len(filtered) >= 3:
                            false_cards_pool = filtered

        if not false_cards_pool:
            false_cards_pool = [c for c in sample if c["name"] != main_card["name"] and is_clean_card(c)]

        false_choices = random.sample(false_cards_pool, k=3)
        options = false_choices + [main_card]
        random.shuffle(options)

        desc_censored = self.censor_card_name(main_card["desc"], main_card["name"]).replace("\n", " ")

        embed = discord.Embed(
            title="🧠 Devine la carte Yu-Gi-Oh !",
            description=desc_censored,
            color=discord.Color.blurple()
        )
        for i, card in enumerate(options):
            embed.add_field(name=REACTIONS[i], value=card["name"], inline=False)

        msg = await ctx.send(embed=embed)
        for reaction in REACTIONS:
            await msg.add_reaction(reaction)

        self.active_sessions[guild_id] = msg

        def check(reaction, user):
            return (
                reaction.message.id == msg.id and
                user != self.bot.user and
                str(reaction.emoji) in REACTIONS
            )

        await asyncio.sleep(60)

        msg = await ctx.channel.fetch_message(msg.id)
        counts = {emoji: 0 for emoji in REACTIONS}
        for reaction in msg.reactions:
            if str(reaction.emoji) in REACTIONS:
                counts[str(reaction.emoji)] = reaction.count - 1

        correct_index = options.index(main_card)
        correct_emoji = REACTIONS[correct_index]

        result_lines = []
        for emoji, card in zip(REACTIONS, options):
            mark = "✅" if emoji == correct_emoji else "❌"
            result_lines.append(f"{emoji} {card['name']} {mark} ({counts[emoji]} vote{'s' if counts[emoji] != 1 else ''})")

        result_text = "\n".join(result_lines)
        await ctx.send(f"🧾 Résultats :\n{result_text}")

        self.active_sessions[guild_id] = None

# ────────────────────────────────────────────────────────────────
# 🔌 SETUP DU COG
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Question(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"  # 📚 Pour l’organisation des commandes
    await bot.add_cog(cog)
