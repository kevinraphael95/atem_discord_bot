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
        "hero", "infinitrack", "kaiser", "kozaky", "labrynth", "live☆twin", "lunar light", "madolche", "marincess",
        "Mekk-Knight", "metalfoes", "naturia", "noble knight", "number", "numero", "numéro", 
        "oni", "Performapal", "phantasm spiral", "pot", "prophecy", "punk", "rescue", "rose dragon", 
        "salamangreat", "sky striker", "tri-brigade", "unchained"
    ]
    name = card.get("name", "").lower()
    return all(keyword not in name for keyword in banned_keywords)


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
            random.shuffle(sample)

            main_card = next((c for c in sample if "name" in c and "desc" in c), None)
            if not main_card:
                await ctx.send("❌ Aucune carte trouvée.")
                self.active_sessions[guild_id] = None
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
                    and is_clean_card(c)
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
                embed.add_field(name="⚙️ Niveau", value=str(true_card.get("level", "—")), inline=True)

            # Options de réponses
            options_str = ""
            for idx, choice in enumerate(all_choices):
                options_str += f"{REACTIONS[idx]} - **{choice}**\n"
            embed.add_field(name="Choix possibles", value=options_str, inline=False)

            quiz_msg = await ctx.send(embed=embed)

            # Ajouter réactions pour que tout le monde puisse réagir
            for r in REACTIONS[:len(all_choices)]:
                await quiz_msg.add_reaction(r)

            # Stocker le message du quiz en cours pour la guild
            self.active_sessions[guild_id] = quiz_msg

            answers = {}

            def check(reaction, user):
                return (
                    reaction.message.id == quiz_msg.id
                    and reaction.emoji in REACTIONS[:len(all_choices)]
                    and not user.bot
                    and user.id not in answers  # ✅ Empêche les doubles réponses
                )


            winners = set()
            answers = {}

            # Attendre 60 secondes pour collecter les réactions
            try:
                while True:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    idx = REACTIONS.index(reaction.emoji)
                    selected_name = all_choices[idx]
                    if user.id not in answers:
                        answers[user.id] = selected_name
                        if selected_name == true_card["name"]:
                            winners.add(user)
                            await self.update_streak(str(user.id), True)
                        else:
                            await self.update_streak(str(user.id), False)
            except asyncio.TimeoutError:
                # Temps écoulé, afficher résultats
                self.active_sessions[guild_id] = None

                correct_index = all_choices.index(true_card["name"])
                reponse = f"{REACTIONS[correct_index]} **{true_card['name']}**"

                # Création de l'embed final
                result_embed = discord.Embed(
                    title="⏰ Le temps est écoulé !",
                    description=(
                        f"✅ La réponse était : {reponse}\n\n"
                        + (
                            f"🎉 **Gagnants :** {', '.join(w.mention for w in winners)}"
                            if winners
                            else "😢 Personne n'a trouvé la bonne réponse..."
                        )
                    ),
                    color=discord.Color.green() if winners else discord.Color.red()
                )
                result_embed.set_footer(text="Merci d'avoir joué !")

                await quiz_msg.channel.send(embed=result_embed)


        except Exception as e:
            self.active_sessions[guild_id] = None
            await ctx.send(f"❌ Une erreur est survenue : `{e}`")





# ────────────────────────────────────────────────────────────────
# 🔌 SETUP DU COG
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Question(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"  # 📚 Pour l’organisation des commandes
    await bot.add_cog(cog)
