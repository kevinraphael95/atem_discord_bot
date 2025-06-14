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
        escaped_name = re.escape(name)
        # Remplace toutes les occurrences insensibles à la casse par des █
        return re.sub(escaped_name, lambda m: "█" * len(m.group()), desc, flags=re.IGNORECASE)

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
                title="🧠 Essayez de trouver le nom de cette carte grace à sa description. (tout le monde peut jouer)",
                description=(
                    f"📘 **T**
