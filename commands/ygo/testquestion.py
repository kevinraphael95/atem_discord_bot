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
# GET VALID CARD, SI LA MAIN CARD A UN ARCHETYPE SUE Y4AI 10 CARTES DE LARCHETYPE MINIMUM SINON ESSAYER ENORE ET ENCORE
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
class TestQuestion(bot)commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # 🔁 Référence au bot
        # Stocke le message du quiz en cours pour chaque guild
        self.active_sessions = {}  # guild_id : discord.Message ou None

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
        name="testquestion",
        aliases=["tq"],
        help="🧠 Devine une carte Yu-Gi-Oh à partir de sa description. Tout le monde peut participer pendant 1 minute !"
    )
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def TestQuestion(bot)self, ctx):
        # Ici tu peux appeler ta fonction get_valid_card
        sample = await self.fetch_card_sample(limit=60)
        main_card = await get_valid_card(sample, min_count=11)
        if not main_card:
            await ctx.send("❌ Aucune carte valide trouvée.")
            return
            
        guild_id = ctx.guild.id if ctx.guild else None

        # Partie active ? on récupère le message Discord
        if guild_id in self.active_sessions and self.active_sessions[guild_id]:
            quiz_msg = self.active_sessions[guild_id]
            # Répondre en reply sous le message du quiz en cours
            await quiz_msg.reply("⚠️ Une partie est déjà en cours dans ce serveur. Patientez qu'elle se termine.", mention_author=False)
            return

        # Marquer la partie comme active (en attente)
        self.active_sessions[guild_id] = None

        try:
            sample = await self.fetch_card_sample(limit=60)
            random.shuffle(sample)

            # On va chercher une carte principale valide, avec archétype dispo en assez grand nombre
            main_card = None

            for card in sample:
                if "name" not in card or "desc" not in card:
                    continue

                archetype = card.get("archetype")
                if archetype:
                    # Vérifier qu'il y a au moins 10 autres cartes avec ce même archétype via l'API
                    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if len(data.get("data", [])) >= 11:  # au moins 11 cartes (1 principale + 10 autres)
                                    main_card = card
                                    break
                            else:
                                continue
                else:
                    # Carte sans archétype, on l'accepte directement
                    main_card = card
                    break

            if not main_card:
                await ctx.send("❌ Aucune carte trouvée avec un archétype suffisamment grand.")
                self.active_sessions[guild_id] = None
                return

            archetype = main_card.get("archetype")
            # ────────────────────────────────────────────────────────────
            # 🆕 MODIFICATION IMPORTANTE : choix des fausses cartes
            # Si la carte a un archétype avec au moins 10 autres cartes,
            # alors on tire toutes les fausses cartes dans ce même archétype.
            # Sinon, on tire les fausses cartes de l'échantillon global.
            # ────────────────────────────────────────────────────────────

            if archetype:
                # On récupère toutes les cartes de cet archétype via l'API
                url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            archetype_cards = data.get("data", [])
                        else:
                            archetype_cards = []

                # Filtrer celles qui ne sont pas la carte principale, et valides
                false_cards_pool = [c for c in archetype_cards if c["name"] != main_card["name"] and is_clean_card(c)]

                if len(false_cards_pool) < 3:
                    # Trop peu, on complète avec l'échantillon global filtré
                    false_cards_pool = [c for c in sample if c["name"] != main_card["name"] and is_clean_card(c)]
            else:
                # Pas d'archétype ou pas assez grand, fausses cartes dans l'échantillon global
                false_cards_pool = [c for c in sample if c["name"] != main_card["name"] and is_clean_card(c)]

            # On choisit 3 fausses cartes aléatoires
            false_choices = random.sample(false_cards_pool, k=3)

            # On prépare la liste finale des 4 choix mélangés
            options = false_choices + [main_card]
            random.shuffle(options)

            # Création du texte description censuré
            desc_censored = self.censor_card_name(main_card["desc"], main_card["name"])
            desc_censored = desc_censored.replace("\n", " ")

            # Construire l’embed avec description et les options
            embed = discord.Embed(
                title="🧠 Devine la carte Yu-Gi-Oh !",
                description=desc_censored,
                color=discord.Color.blurple()
            )
            for i, card in enumerate(options):
                embed.add_field(name=REACTIONS[i], value=card["name"], inline=False)

            msg = await ctx.send(embed=embed)

            # Ajouter les réactions pour la réponse
            for reaction in REACTIONS:
                await msg.add_reaction(reaction)

            self.active_sessions[guild_id] = msg

            def check(reaction, user):
                return (
                    reaction.message.id == msg.id and
                    user != self.bot.user and
                    str(reaction.emoji) in REACTIONS
                )

            # Attendre 60 secondes ou la première bonne réponse
            try:
                while True:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    selected_index = REACTIONS.index(str(reaction.emoji))
                    selected_card = options[selected_index]

                    if selected_card["name"] == main_card["name"]:
                        await ctx.send(f"✅ Bravo {user.mention}, c'était bien **{main_card['name']}** !")
                        await self.update_streak(str(user.id), True)
                        break
                    else:
                        await ctx.send(f"❌ Désolé {user.mention}, ce n'est pas la bonne carte.")
                        await self.update_streak(str(user.id), False)

            except asyncio.TimeoutError:
                await ctx.send(f"⌛ Temps écoulé ! La bonne réponse était **{main_card['name']}**.")

            self.active_sessions[guild_id] = None

        except Exception as e:
            self.active_sessions[guild_id] = None
            await ctx.send(f"❌ Une erreur est survenue : {e}")

# ────────────────────────────────────────────────────────────────
# 🔌 SETUP DU COG
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestQuestion(bot)bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"  # 📚 Pour l’organisation des commandes
    await bot.add_cog(cog)
