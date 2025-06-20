# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Question.py — Commande !question
# Objectif : Deviner une carte Yu-Gi-Oh à partir de sa description parmi 4 choix
# Bonus : suivi de série de bonnes réponses (streak) enregistré via Supabase
# ────────────────────────────────────────────────────────────────────────────────

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
        "eyes of blue", "punk", "fur hire", "dark world", "dragonmaid",
        "sky striker", "labrynth", "floowandereeze", "marincess", "salamangreat",
        "tri-brigade", "madolche", "phantasm spiral", "f.a.", "f.a", "abc-", "abc -", "live☆twin",
        "branded", "cloudian", "hero", "kozaky", "kaiser", "metalfoes", "number", "oni"
    ]
    name = card.get("name", "").lower()
    return all(keyword not in name for keyword in banned_keywords)

# ────────────────────────────────────────────────────────────────
# 🧩 CLASSE DU COG
# ────────────────────────────────────────────────────────────────
class Question(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # 🔁 Référence au bot

    # ────────────────────────────────────────────────────────
    # 🔄 Récupère un échantillon aléatoire de cartes
    # ────────────────────────────────────────────────────────
    async def fetch_card_sample(self, limit=100):
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return random.sample(data.get("data", []), min(limit, len(data.get("data", []))))

    # ────────────────────────────────────────────────────────
    # 🔒 Censure le nom de la carte dans sa description
    # ────────────────────────────────────────────────────────
    def censor_card_name(self, desc: str, name: str) -> str:
        return re.sub(re.escape(name), "[cette carte]", desc, flags=re.IGNORECASE)

    # ────────────────────────────────────────────────────────
    # 🔁 Met à jour le streak de l’utilisateur
    # ────────────────────────────────────────────────────────
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

    # ────────────────────────────────────────────────────────────────
    # ❓ COMMANDE !question
    # Deviner une carte à partir de sa description censurée
    # ────────────────────────────────────────────────────────────────
    @commands.command(
        name="question",
        aliases=["q"],
        help="🧠 Devine une carte Yu-Gi-Oh à partir de sa description. Tout le monde peut participer pendant 1 minute !"
    )
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def Question(self, ctx):
        try:
            sample = await self.fetch_card_sample(limit=60)
            random.shuffle(sample)

            main_card = next((c for c in sample if "name" in c and "desc" in c), None)
            if not main_card:
                await ctx.send("❌ Aucune carte trouvée.")
                return

            archetype = main_card.get("archetype")
            main_type = main_card.get("type", "").lower()
            type_group = "monstre" if "monstre" in main_type else ("magie" if "magie" in main_type else "piège")
            group = []

            if not archetype:
                group = [
                    c for c in sample
                    if c.get("name") != main_card["name"]
                    and "desc" in c
                    and c.get("type", "").lower() == main_type
                    and not c.get("archetype")
                    and is_clean_card(c)  # 👈 ici on applique ton filtre de mots-clés
                ]

            else:
                url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            arch_sample = random.sample(data.get("data", []), min(60, len(data.get("data", []))))
                            group = [
                                c for c in arch_sample
                                if c.get("name") != main_card["name"]
                                and "desc" in c
                                and c.get("type", "").lower() == main_type
                            ]
                            if len(group) < 3:
                                group = [
                                    c for c in arch_sample
                                    if c.get("name") != main_card["name"]
                                    and "desc" in c
                                    and type_group in c.get("type", "").lower()
                                ]

            if len(group) < 3:
                group = [
                    c for c in sample
                    if c.get("name") != main_card["name"]
                    and "desc" in c
                    and type_group in c.get("type", "").lower()
                ]
            if len(group) < 3:
                group = random.sample(
                    [c for c in sample if c.get("name") != main_card["name"] and "desc" in c],
                    3
                )

            true_card = main_card
            wrongs = random.sample(group, 3)
            all_choices = [true_card["name"]] + [c["name"] for c in wrongs]
            random.shuffle(all_choices)

            censored = self.censor_card_name(true_card["desc"], true_card["name"])
            image_url = true_card.get("card_images", [{}])[0].get("image_url_cropped")

            embed = discord.Embed(
                title="🧠 Quelle est le nom de cette carte ? (tout le monde peut jouer)",
                description=(
                    f"📘 **Type :** {true_card.get('type', '—')}\n"
                    f"📝 **Description :**\n*{censored[:1500]}{'...' if len(censored) > 1500 else ''}*"
                ),
                color=discord.Color.purple()
            )
            embed.set_author(name="Trouvez le nom de la carte", icon_url="https://cdn-icons-png.flaticon.com/512/361/361678.png")
            # if image_url:
            #     embed.set_thumbnail(url=image_url)

            embed.add_field(name="🔹 Archétype", value=f"||{archetype or 'Aucun'}||", inline=False)

            if main_type.startswith("monstre"):
                embed.add_field(name="💥 ATK", value=str(true_card.get("atk", "—")), inline=True)
                embed.add_field(name="🛡️ DEF", value=str(true_card.get("def", "—")), inline=True)
                embed.add_field(name="⭐ Niveau", value=str(true_card.get("level", "—")), inline=True)
                embed.add_field(name="🌪️ Attribut", value=true_card.get("attribute", "—"), inline=True)

            embed.add_field(
                name="❓ Choisis la bonne carte :",
                value="\n".join(f"{REACTIONS[i]} {name}" for i, name in enumerate(all_choices)),
                inline=False
            )
            embed.set_footer(text="Vous avez 60 secondes pour répondre ! Réagissez avec l’emoji correspondant à votre réponse👇")

            msg = await ctx.send(embed=embed)
            for emoji in REACTIONS:
                await msg.add_reaction(emoji)

            user_answers = {}  # user_id -> emoji

            def check(reaction, user):
                return (
                    reaction.message.id == msg.id
                    and str(reaction.emoji) in REACTIONS
                    and not user.bot
                    and user.id not in user_answers
                )

            try:
                while True:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    user_answers[user.id] = str(reaction.emoji)
            except asyncio.TimeoutError:
                pass

            correct_index = all_choices.index(true_card["name"])
            correct_emoji = REACTIONS[correct_index]
            winners = [await self.bot.fetch_user(uid) for uid, emoji in user_answers.items() if emoji == correct_emoji]
            participants = [await self.bot.fetch_user(uid) for uid in user_answers]
            losers = [u for u in participants if u not in winners]

            for user in winners:
                await self.update_streak(str(user.id), correct=True)
            for user in losers:
                await self.update_streak(str(user.id), correct=False)

            result_embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=f"La bonne réponse était : {REACTIONS[correct_index]} **{true_card['name']}**",
                color=discord.Color.green()
            )
            if winners:
                noms = "\n".join(f"✅ {user.mention}" for user in winners)
                result_embed.add_field(name="Bravo à :", value=noms, inline=False)
            else:
                result_embed.add_field(name="Aucun gagnant 😢", value="Personne n’a trouvé la bonne réponse.")

            await ctx.send(embed=result_embed)

        except Exception as e:
            print("[ERREUR QUESTION]", e)
            await ctx.send("🚨 Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────
# 🔌 SETUP DU COG
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Question(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"  # 📚 Pour l’organisation des commandes
    await bot.add_cog(cog)
