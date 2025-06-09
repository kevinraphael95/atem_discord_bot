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
        return re.sub(re.escape(name), "█" * len(name), desc, flags=re.IGNORECASE)

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
        help="🧠 Devine une carte Yu-Gi-Oh à partir de sa description. Essaie de faire la plus grande série de bonnes réponses. (jeu solo)"
    )
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def Question(self, ctx):
        try:
            # ───────────────────────────────
            # 🧪 Étape 1 : Échantillon initial
            # ───────────────────────────────
            sample = await self.fetch_card_sample(limit=60)
            random.shuffle(sample)

            # 🔍 Trouver une carte avec nom + description
            main_card = next((c for c in sample if "name" in c and "desc" in c), None)
            if not main_card:
                await ctx.send("❌ Aucune carte trouvée.")
                return

            # ───────────────────────────────
            # 🧩 Étape 2 : Sélection des propositions
            # ───────────────────────────────
            archetype = main_card.get("archetype")
            main_type = main_card.get("type", "").lower()
            type_group = "monstre" if "monstre" in main_type else ("magie" if "magie" in main_type else "piège")

            group = []

            # ▶️ Si pas d’archétype : filtrer par type
            if not archetype:
                group = [
                    c for c in sample
                    if c.get("name") != main_card["name"]
                    and "desc" in c
                    and c.get("type", "").lower() == main_type
                    and not c.get("archetype") 
                ]
            else:
                # 🔁 Tentative de récupération par archétype
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
                            # 🔄 Sinon : même grande famille
                            if len(group) < 3:
                                group = [
                                    c for c in arch_sample
                                    if c.get("name") != main_card["name"]
                                    and "desc" in c
                                    and type_group in c.get("type", "").lower()
                                ]

            # 🔁 Fallbacks si pas assez de cartes
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

            # ───────────────────────────────
            # 📊 Étape 3 : Construction du quiz
            # ───────────────────────────────
            true_card = main_card
            wrongs = random.sample(group, 3)
            all_choices = [true_card["name"]] + [c["name"] for c in wrongs]
            random.shuffle(all_choices)

            # 🕶️ Censure description
            censored = self.censor_card_name(true_card["desc"], true_card["name"])

            # 📎 Image
            image_url = true_card.get("card_images", [{}])[0].get("image_url_cropped")

            # 🧾 Construction de l'embed
            embed = discord.Embed(
                title="🧠 Quelle est cette carte ?",
                description=(
                    f"📘 **Type :** {true_card.get('type', '—')}\n"
                    f"📝 **Description :**\n*{censored[:500]}{'...' if len(censored) > 300 else ''}*"
                ),
                color=discord.Color.purple()
            )
            embed.set_author(name="YGO Quiz", icon_url="https://cdn-icons-png.flaticon.com/512/361/361678.png")
            if image_url:
                embed.set_thumbnail(url=image_url)

            embed.add_field(name="🔹 Archétype", value=f"||{archetype or 'Aucun'}||", inline=False)

            # 💥 Statistiques (si monstre)
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
            embed.set_footer(text="Réagis avec l'emoji correspondant à ta réponse👇\n Fais questionscore (ou qs) pour voir ton score et questionscoretop (ou qst) pour voir les meilleurs score de tous les joueurs.")

            # Envoi de l'embed + réactions
            msg = await ctx.send(embed=embed)
            for emoji in REACTIONS[:4]:
                await msg.add_reaction(emoji)

            # ⏳ Attente de la réaction
            def check(reaction, user):
                return user == ctx.author and reaction.message.id == msg.id and str(reaction.emoji) in REACTIONS

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=600.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send("⏰ Temps écoulé !")
                return

            # 📈 Résultat
            selected_index = REACTIONS.index(str(reaction.emoji))
            correct_index = all_choices.index(true_card["name"])
            user_id = str(ctx.author.id)

            if selected_index == correct_index:
                await self.update_streak(user_id, correct=True)
                await ctx.send(f"✅ Bonne réponse ! C’était **{true_card['name']}**.")
            else:
                await self.update_streak(user_id, correct=False)
                await ctx.send(f"❌ Mauvaise réponse ! C’était **{true_card['name']}**.")

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
