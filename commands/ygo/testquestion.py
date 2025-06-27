# ────────────────────────────────────────────────────────────────────────────────
# 🧠 TestQuestion.py — Commande !TestQuestion
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
from difflib import SequenceMatcher  # Ajoute ça en haut si ce n’est pas déjà fait

# Réactions pour les 4 propositions
REACTIONS = ["🇦", "🇧", "🇨", "🇩"]


# ────────────────────────────────────────────────────────────────
# 🔐 Empêcher l'utilisation en MP
# ────────────────────────────────────────────────────────────────
def no_dm():
    async def predicate(ctx):
        if ctx.guild is None:
            await ctx.send("❌ Cette commande ne peut pas être utilisée en MP.")
            return False
        return True
    return commands.check(predicate)

# ────────────────────────────────────────────────────────────────
# 📚 FONCTIONS UTILITAIRES
# ────────────────────────────────────────────────────────────────
def similarity_ratio(a: str, b: str) -> float:
    # Retourne le ratio de similarité entre deux noms (0 à 1)
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def common_word_score(name1, name2):
    # Compte le nombre de mots en commun entre deux noms de cartes
    words1 = set(name1.lower().split())
    words2 = set(name2.lower().split())
    return len(words1 & words2)

def is_clean_card(card):
    # Filtre les cartes contenant des mots bannis (métas, spams...)
    banned_keywords = [
        "@Ignister", "abc -", "abc-", "abyss", "ancient gear", "altergeist", "archfiend", "assaut de l'air", 
        "air assault", "beetrouper", "branded", "cloudian", 
        "crusadia", "cyber", "cynet", "D.D.", "dark magician", "dark world", "dinowrestler", 
        "dragonmaid", "dragon ruler", "dragunity", "exosister", "eyes of blue", "yeux de bleu", "f.a", "f.a.", 
        "floowandereeze", "fur hire", "gearfried", "genex", "harpie", 
        "hero", "héro", "héros", "hurricail", "infinitrack", "kaiser", "kozaky", 
        "labrynth", "live☆twin", "lunar light", "madolche", "marincess",
        "Mekk-Knight", "metalfoes", "naturia", "noble knight", "number", "numero", "numéro", 
        "oni", "Performapal", "phantasm spiral", "Phantom Knights", "pot", 
        "prophecy", "psychic", "punk", "rescue", "rose dragon", 
        "salamangreat", "six samurai", "sky striker", "usnavalon", "tierra", 
        "Traptrix", "tri-brigade", "unchained", "zoodiac"
    ]
    name = card.get("name", "").lower()
    return all(kw.lower() not in name for kw in banned_keywords)

def censor_card_name(desc: str, name: str) -> str:
    # Remplace le nom exact de la carte dans sa description par [cette carte]
    return re.sub(re.escape(name), "[cette carte]", desc, flags=re.IGNORECASE)

def get_significant_words(name):
    # Récupère les mots de 3 lettres ou plus (exclut "de", "la", etc.)
    return set(word.lower() for word in re.findall(r'\b\w{3,}\b', name))


# ────────────────────────────────────────────────────────────────
# 🔍 SÉLECTION D'UNE CARTE PRINCIPALE VALIDE
# ────────────────────────────────────────────────────────────────
async def fetch_card_sample(limit=100):
    # Récupère un échantillon aléatoire de cartes depuis l'API
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return random.sample(data.get("data", []), min(limit, len(data.get("data", []))))

async def get_valid_card(sample, min_count=11):
    # Tente de sélectionner une carte avec un archétype suffisant OU aucune
    archetype_cache = {}
    for _ in range(30):
        card = random.choice(sample)
        if not is_clean_card(card):
            continue
        archetype = card.get("archetype")
        if not archetype:
            return card  # Pas d'archétype, carte valide
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
# 🔄 MISE À JOUR DU STREAK DANS SUPABASE
# ────────────────────────────────────────────────────────────────
async def update_streak(user_id: str, correct: bool):
    data = supabase.table("ygo_streaks").select("*").eq("user_id", user_id).execute()
    row = data.data[0] if data.data else None
    new_streak = (row["current_streak"] + 1 if correct else 0) if row else (1 if correct else 0)
    best = max(row.get("best_streak", 0), new_streak) if row else new_streak
    payload = {"user_id": user_id, "current_streak": new_streak, "best_streak": best}
    if row:
        supabase.table("ygo_streaks").update(payload).eq("user_id", user_id).execute()
    else:
        supabase.table("ygo_streaks").insert(payload).execute()

# ────────────────────────────────────────────────────────────────
# 🧠 COG PRINCIPAL — TestQuestion
# ────────────────────────────────────────────────────────────────
class TestQuestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}  # Guild ID -> Message de quiz actif

    @commands.command(name="testquestion", aliases=["tq"], help="🧠 Devine une carte Yu-Gi-Oh par sa description")
    @no_dm()
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def test_question(self, ctx):
        guild_id = ctx.guild.id

        # Ne pas démarrer si un quiz est déjà actif
        if self.active_sessions.get(guild_id):
            await ctx.reply("⚠️ Un quiz est déjà en cours.", mention_author=False)
            return

        self.active_sessions[guild_id] = True  # Marque comme actif
        try:
            sample = await fetch_card_sample()
            main_card = await get_valid_card(sample)
            if not main_card:
                await ctx.send("❌ Aucune carte valide trouvée.")
                self.active_sessions[guild_id] = None
                return

            archetype = main_card.get("archetype")
            main_type = main_card.get("type", "").lower()
            type_group = "monstre" if "monstre" in main_type else ("magie" if "magie" in main_type else "piège")

            # 🔍 Choix des fausses cartes
            group = []
            if not archetype:
                # Si pas d'archétype, chercher des cartes du même type sans archétype et avec mots en commun
                main_words = get_significant_words(main_card["name"])
                candidates = [
                    c for c in sample
                    if c.get("name") != main_card["name"]
                    and "desc" in c
                    and c.get("type", "").lower() == main_type
                    and not c.get("archetype")
                    and is_clean_card(c)
                    and get_significant_words(c["name"]) & main_words  # au moins un mot en commun
                ]

                group = candidates[:10]
            else:
                # Si archétype, récupérer d'autres cartes du même archétype
                url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            arch_sample = data.get("data", [])
                            group = [
                                c for c in arch_sample
                                if c.get("name") != main_card["name"]
                                and "desc" in c
                                and c.get("type", "").lower() == main_type
                            ]
                            if len(group) < 10:
                                group += [
                                    c for c in arch_sample
                                    if c.get("name") != main_card["name"]
                                    and "desc" in c
                                    and type_group in c.get("type", "").lower()
                                    and c not in group
                                ]

            if len(group) < 3:
                # Fallback : mêmes types globaux ou aléatoire si pas assez
                group = [
                    c for c in sample
                    if c.get("name") != main_card["name"] and "desc" in c and type_group in c.get("type", "").lower()
                ]
                if len(group) < 3:
                    group = random.sample([c for c in sample if c.get("name") != main_card["name"] and "desc" in c], 3)

            group = [c for c in group if is_clean_card(c)]
            wrongs = random.sample(group, 3)
            all_choices = [main_card["name"]] + [c["name"] for c in wrongs]
            random.shuffle(all_choices)

            # 📜 Création de l'embed question
            censored = censor_card_name(main_card["desc"], main_card["name"])
            embed = discord.Embed(
                title="🧠 Quelle est cette carte ?",
                description=(
                    f"📘 **Type :** {main_card.get('type', '—')}\n"
                    f"📝 *{censored[:1500]}{'...' if len(censored) > 1500 else ''}*"
                ),
                color=discord.Color.purple()
            )
            embed.add_field(name="🔹 Archétype", value=f"||{archetype or 'Aucun'}||", inline=False)
            if main_type.startswith("monstre"):
                embed.add_field(name="💥 ATK", value=str(main_card.get("atk", "—")), inline=True)
                embed.add_field(name="🛡️ DEF", value=str(main_card.get("def", "—")), inline=True)
                embed.add_field(name="⚙️ Niveau", value=str(main_card.get("level", "—")), inline=True)

            options_str = "\n".join(f"{REACTIONS[i]} - **{name}**" for i, name in enumerate(all_choices))
            embed.add_field(name="Choix", value=options_str, inline=False)

            quiz_msg = await ctx.send(embed=embed)
            self.active_sessions[guild_id] = quiz_msg

            for r in REACTIONS[:len(all_choices)]:
                await quiz_msg.add_reaction(r)

            answers = {}
            winners = set()

            def check(reaction, user):
                return reaction.message.id == quiz_msg.id and reaction.emoji in REACTIONS[:len(all_choices)] and not user.bot and user.id not in answers

            try:
                while True:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    idx = REACTIONS.index(reaction.emoji)
                    chosen = all_choices[idx]
                    answers[user.id] = chosen
                    if chosen == main_card["name"]:
                        winners.add(user)
                        await update_streak(str(user.id), True)
                    else:
                        await update_streak(str(user.id), False)
            except asyncio.TimeoutError:
                correct_emoji = REACTIONS[all_choices.index(main_card["name"])]
                embed_result = discord.Embed(
                    title="⏰ Temps écoulé !",
                    description=f"✅ Réponse : {correct_emoji} **{main_card['name']}**\n\n" + (
                        f"🎉 Gagnants : {', '.join(w.mention for w in winners)}"
                        if winners else "😢 Personne n'a trouvé..."
                    ),
                    color=discord.Color.green() if winners else discord.Color.red()
                )
                await ctx.send(embed=embed_result)
                self.active_sessions[guild_id] = None

        except Exception as e:
            self.active_sessions[guild_id] = None
            await ctx.send(f"❌ Erreur : `{e}`")

# ────────────────────────────────────────────────────────────────
# 🔌 SETUP DU COG
# ────────────────────────────────────────────────────────────────
async def setup(bot):
    cog = TestQuestion(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
