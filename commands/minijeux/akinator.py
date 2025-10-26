# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande /akinator et !akinator
# Objectif : Mini-jeu Akinator Yu-Gi-Oh! devinant la carte à laquelle le joueur pense
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 1 utilisation / 15 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from utils.discord_utils import safe_send, safe_edit
import aiohttp
import asyncio
import json
import random

QUESTIONS_JSON_PATH = "data/akinator_questions.json"

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Fonction utilitaire : chargement des questions
# ────────────────────────────────────────────────────────────────────────────────
def load_questions():
    try:
        with open(QUESTIONS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR] Impossible de charger {QUESTIONS_JSON_PATH}: {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Classe principale de l’Akinator (logique de jeu)
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorView(View):
    def __init__(self, bot, questions, cards):
        super().__init__(timeout=300)
        self.bot = bot
        self.questions = questions
        self.remaining_cards = cards
        self.message = None
        self.current_question = None
        self.current_value = None
        self.asked = set()
        self.question_count = 0

    # 🔹 Choix de la meilleure question
    def choose_best_question(self):
        best_q = None
        best_balance = float("inf")
        for q in self.questions:
            key = q.get("filter_key")
            if not key or key in self.asked:
                continue
            values = q.get("filter_value", [])
            available_values = [
                v for v in values if any(v in c.get(key, []) for c in self.remaining_cards)
            ]
            if not available_values:
                continue
            for val in available_values:
                count_yes = sum(1 for c in self.remaining_cards if val in c.get(key, []))
                count_no = len(self.remaining_cards) - count_yes
                balance = abs(count_yes - count_no)
                if balance < best_balance:
                    best_balance = balance
                    best_q = q
                    self.current_value = val
        return best_q

    # 🔹 Pose la question suivante
    async def ask_question(self, interaction=None):
        top_cards = sorted(self.remaining_cards, key=lambda c: c.get("atk", 0), reverse=True)[:3]
        can_propose = self.question_count >= 8 or len(self.remaining_cards) <= 3

        if can_propose or not self.remaining_cards:
            embed = discord.Embed(
                title="🔮 Résultat Akinator",
                description=(
                    "Voici mes meilleures prédictions :\n\n"
                    + "\n".join(f"• **{c['name']}**" for c in top_cards)
                    if top_cards else "❌ Aucune carte correspondante trouvée."
                ),
                color=discord.Color.purple()
            )
            if top_cards and "card_images" in top_cards[0]:
                embed.set_image(url=top_cards[0]["card_images"][0].get("image_url", ""))

            await safe_edit(self.message, embed=embed, view=None)
            return

        q = self.choose_best_question()
        if not q:
            await safe_edit(self.message, content="❌ Plus de questions disponibles.", view=None)
            return

        self.current_question = q
        self.asked.add(q["filter_key"])
        question_text = (q.get("text") or "").replace("{value}", self.current_value or "…")

        embed = discord.Embed(
            title="❓ Question Akinator",
            description=f"{question_text}\n\n({len(self.remaining_cards)} cartes restantes)",
            color=discord.Color.blue()
        )

        self.clear_items()
        for label in ["Oui", "Non", "Ne sais pas", "Abandonner"]:
            style = discord.ButtonStyle.danger if label == "Abandonner" else discord.ButtonStyle.primary
            self.add_item(AkinatorButton(self, label, style))

        await safe_edit(self.message, embed=embed, view=self)

    # 🔹 Réponse du joueur
    async def process_answer(self, answer: str, interaction: discord.Interaction):
        if answer == "Abandonner":
            await safe_edit(self.message, embed=discord.Embed(
                title="🛑 Partie arrêtée",
                description="Tu as abandonné l'Akinator.",
                color=discord.Color.red()
            ), view=None)
            return

        q, val = self.current_question, self.current_value
        key = q.get("filter_key")

        if answer == "Oui":
            self.remaining_cards = [c for c in self.remaining_cards if val in c.get(key, [])]
        elif answer == "Non":
            self.remaining_cards = [c for c in self.remaining_cards if val not in c.get(key, [])]

        self.question_count += 1
        await self.ask_question()

# ────────────────────────────────────────────────────────────────────────────────
# 🔘 Boutons de réponses
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorButton(Button):
    def __init__(self, view, label, style=discord.ButtonStyle.primary):
        super().__init__(label=label, style=style)
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        await self.view.process_answer(self.label, interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🔘 Bouton "Commencer"
# ────────────────────────────────────────────────────────────────────────────────
class StartButton(Button):
    def __init__(self, view, label="Commencer"):
        super().__init__(label=label, style=discord.ButtonStyle.success)
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        self.view.message = interaction.message
        self.view.clear_items()
        await self.view.ask_question()

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Cog principal : Commande Akinator
# ────────────────────────────────────────────────────────────────────────────────
class Akinator(commands.Cog):
    """
    Commande /akinator et !akinator — Fait deviner une carte Yu-Gi-Oh! à l’Akinator
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 📥 Téléchargement aléatoire de cartes (max 150, sûr)
    async def fetch_random_cards(self, limit=150):
        safe_limit = min(limit, 150)
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"[ERREUR] Impossible de récupérer les cartes: HTTP {resp.status}")
                    return []
                data = await resp.json()

        all_cards = data.get("data", [])
        if not all_cards:
            return []

        sampled_cards = random.sample(all_cards, min(safe_limit, len(all_cards)))
        cards = []
        for c in sampled_cards:
            cards.append({
                "id": c.get("id"),
                "name": c.get("name", "Inconnue"),
                "type_subtype": (c.get("type", "") + " " + c.get("race", "")).split(),
                "attribute": [c.get("attribute")] if c.get("attribute") else [],
                "archetype": [c.get("archetype")] if c.get("archetype") else [],
                "effect": ["Effect"] if c.get("desc") and "effect" in c.get("desc").lower() else ["Normal"],
                "level": c.get("level", 0),
                "atk": c.get("atk", 0),
                "def": c.get("def", 0),
                "linkval": c.get("linkval", 0),
                "card_images": c.get("card_images", []),
            })

        return cards

    # 🎮 Lancement du jeu
    async def start_akinator(self, ctx_or_interaction):
        questions = load_questions()
        if not questions:
            await safe_send(ctx_or_interaction, "❌ Impossible de charger les questions.")
            return

        cards = await self.fetch_random_cards()
        if not cards:
            await safe_send(ctx_or_interaction, "❌ Impossible de récupérer les cartes.")
            return

        view = AkinatorView(self.bot, questions, cards)

        embed = discord.Embed(
            title="🎩 Akinator Yu-Gi-Oh!",
            description="Pense à une carte Yu-Gi-Oh! et clique sur **Commencer** pour débuter le jeu.",
            color=discord.Color.green()
        )
        view.clear_items()
        view.add_item(StartButton(view))
        view.message = await safe_send(ctx_or_interaction, embed=embed, view=view)

    # ────────── Slash command
    @app_commands.command(name="akinator", description="Laisse Akinator deviner ta carte Yu-Gi-Oh!")
    async def slash_akinator(self, interaction: discord.Interaction):
        await self.start_akinator(interaction)

    # ────────── Prefix command
    @commands.command(name="akinator", help="Laisse Akinator deviner ta carte Yu-Gi-Oh!")
    async def prefix_akinator(self, ctx):
        await self.start_akinator(ctx)



# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Akinator(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
    



