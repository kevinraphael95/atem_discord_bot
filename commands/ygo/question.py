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
# GET VALID CARD
# - Choisit une carte au hasard dans l'échantillon
# - Si archétype, vérifie via API qu'il y a au moins min_count cartes dans cet archétype
# - Sinon, continue jusqu'à max_attempts essais
# ────────────────────────────────────────────────────────────────
async def get_valid_card(sample, min_count=11, max_attempts=30):
    archetype_cache = {}
    attempts = 0

    async with aiohttp.ClientSession() as session:
        while attempts < max_attempts:
            attempts += 1
            card = random.choice(sample)
            archetype = card.get("archetype")
            
            if not archetype:
                # Carte sans archétype, on la valide directement
                return card
            
            if archetype not in archetype_cache:
                url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
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
        name="question",
        aliases=["q"],
        help="🧠 Devine une carte Yu-Gi-Oh à partir de sa description. Tout le monde peut participer pendant 1 minute !"
    )
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def Question(self, ctx):
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
            if not sample:
                await ctx.send("❌ Impossible de récupérer les cartes pour le quiz.")
                self.active_sessions[guild_id] = None
                return

            # Choix de la carte principale valide
            main_card = await get_valid_card(sample, min_count=11)
            if not main_card:
                await ctx.send("❌ Aucune carte valide trouvée avec un archétype assez grand ou sans archétype.")
                self.active_sessions[guild_id] = None
                return

            archetype = main_card.get("archetype")
            main_type = main_card.get("type", "").lower()
            # Simplification du type pour fallback
            type_group = "monstre" if "monstre" in main_type else ("magie" if "magie" in main_type else "piège")

            group = []

            # Construction des fausses réponses selon archétype
            async with aiohttp.ClientSession() as session:
                if archetype:
                    # Récupérer un échantillon dans cet archétype
                    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            arch_cards = data.get("data", [])
                            arch_sample = random.sample(arch_cards, min(60, len(arch_cards)))

                            # Cartes différentes, même type et avec description
                            group = [
                                c for c in arch_sample
                                if c.get("name") != main_card["name"]
                                and "desc" in c and c.get("desc")
                                and (type_group in c.get("type", "").lower())
                            ]
                            if len(group) < 3:
                                group = []  # fallback si pas assez
                # Fallback si pas assez dans archétype ou pas d'archétype
                if not group or len(group) < 3:
                    # Prendre aléatoirement 3 cartes dans l'échantillon filtré qui ne sont pas la carte principale
                    group = [
                        c for c in sample
                        if c.get("name") != main_card["name"]
                        and "desc" in c and c.get("desc")
                        and (type_group in c.get("type", "").lower())
                    ]
                    if len(group) >= 3:
                        group = random.sample(group, 3)
                    else:
                        # Si toujours pas assez, prendre n'importe quoi sauf la carte principale
                        group = [c for c in sample if c.get("name") != main_card["name"]]
                        if len(group) >= 3:
                            group = random.sample(group, 3)
                        else:
                            # Insuffisant, abandonner
                            await ctx.send("❌ Pas assez de cartes disponibles pour générer les réponses.")
                            self.active_sessions[guild_id] = None
                            return

            # On mélange la bonne réponse + 3 fausses
            choices = group[:3] + [main_card]
            random.shuffle(choices)

            # Préparer l'embed
            embed = discord.Embed(
                title="🧩 Devine la carte Yu-Gi-Oh !",
                color=discord.Color.gold()
            )
            # Description censurée
            censored_desc = self.censor_card_name(main_card["desc"], main_card["name"])
            embed.description = f"**Description de la carte :**\n{censored_desc}"

            # Ajouter les propositions avec leurs réactions (A, B, C, D)
            for i, c in enumerate(choices):
                embed.add_field(name=f"{REACTIONS[i]} {c['name']}", value=f"*{c.get('type', 'Type inconnu')}*", inline=False)

            embed.set_footer(text="Réagissez avec 🇦 🇧 🇨 🇩 pour répondre. Vous avez 60 secondes.")

            # Envoyer le message du quiz
            quiz_msg = await ctx.send(embed=embed)
            self.active_sessions[guild_id] = quiz_msg

            # Ajouter les réactions
            for r in REACTIONS:
                await quiz_msg.add_reaction(r)

            def check(reaction, user):
                return (
                    reaction.message.id == quiz_msg.id and
                    str(reaction.emoji) in REACTIONS and
                    not user.bot and
                    (user in ctx.channel.members or ctx.guild is None)
                )

            try:
                # Collecter toutes les réactions pendant 60 secondes
                users_answers = {}  # user_id : choix_indice

                while True:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    choice_index = REACTIONS.index(str(reaction.emoji))
                    users_answers[user.id] = choice_index
            except asyncio.TimeoutError:
                pass

            # Calculer résultats
            correct_index = choices.index(main_card)

            # Préparer les résultats
            winners = [user_id for user_id, ans in users_answers.items() if ans == correct_index]

            # Récupérer les membres depuis l’ID
            winners_mentions = []
            for user_id in winners:
                user = self.bot.get_user(user_id)
                if user:
                    winners_mentions.append(user.mention)

            result_msg = f"🕑 Temps écoulé ! La bonne réponse était **{REACTIONS[correct_index]} {main_card['name']}**.\n"

            if winners_mentions:
                result_msg += "🎉 Bravo à : " + ", ".join(winners_mentions)
            else:
                result_msg += "😞 Personne n'a trouvé la bonne réponse cette fois."

            # Mettre à jour le streak pour chaque participant
            for user_id, ans in users_answers.items():
                correct = (ans == correct_index)
                await self.update_streak(str(user_id), correct)

            # Afficher le message résultat
            await ctx.send(result_msg)

        except Exception as e:
            await ctx.send(f"⚠️ Une erreur est survenue : {e}")

        finally:
            # Fin de partie, libérer la session
            self.active_sessions[guild_id] = None




# ────────────────────────────────────────────────────────────────
# 🔌 SETUP DU COG
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Question(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"  # 📚 Pour l’organisation des commandes
    await bot.add_cog(cog)
