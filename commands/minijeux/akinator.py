# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator_yugioh.py — Akinator Yu-Gi-Oh! probabiliste
# Objectif : Deviner la carte à laquelle le joueur pense
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
import math

QUESTIONS_JSON_PATH = "data/akinator_questions.json"

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Chargement des questions
# ────────────────────────────────────────────────────────────────────────────────
def load_questions():
    try:
        with open(QUESTIONS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR] Impossible de charger {QUESTIONS_JSON_PATH}: {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Vue Akinator
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorView(View):
    def __init__(self, bot, questions, cards):
        super().__init__(timeout=300)
        self.bot = bot
        self.questions = questions
        self.cards = cards
        self.message = None
        self.question_count = 0
        self.max_questions = 12
        self.probabilities = {c["id"]: 1.0 for c in self.cards}  # probabilité initiale
        self.asked_questions = set()
        self.current_question = None

    # 🔹 Choisir la question qui sépare le mieux
    def choose_best_question(self):
        best_q = None
        best_score = -1
        for q in self.questions:
            key = q.get("filter_key")
            if not key or key in self.asked_questions:
                continue

            # Calculer entropie
            yes_count = 0
            no_count = 0
            for c in self.cards:
                val_list = c.get(key, [])
                if any(v in val_list for v in q.get("filter_value", [])):
                    yes_count += self.probabilities[c["id"]]
                else:
                    no_count += self.probabilities[c["id"]]

            total = yes_count + no_count
            if total == 0:
                continue
            yes_ratio = yes_count / total
            no_ratio = no_count / total
            entropy = -sum(p * math.log2(p) for p in [yes_ratio, no_ratio] if p > 0)

            if entropy > best_score:
                best_score = entropy
                best_q = q

        return best_q

    # 🔹 Envoyer embed initial
    def get_initial_embed_and_buttons(self):
        self.clear_items()
        for label in ["Oui", "Non", "Ne sais pas", "Abandonner"]:
            style = discord.ButtonStyle.danger if label == "Abandonner" else discord.ButtonStyle.primary
            self.add_item(AkinatorButton(self, label, style))

        embed = discord.Embed(
            title="🎩 Akinator Yu-Gi-Oh!",
            description="Pense à une carte Yu-Gi-Oh! et je vais essayer de la deviner.",
            color=discord.Color.green()
        )
        return embed

    # 🔹 Proposer la question suivante ou résultat
    async def ask_question(self, interaction=None):
        # Vérifier si une carte dépasse 80% de probabilité
        best_card_id, best_prob = max(self.probabilities.items(), key=lambda x: x[1])
        best_card = next((c for c in self.cards if c["id"] == best_card_id), None)
        if best_prob >= 0.8 or self.question_count >= self.max_questions:
            embed = discord.Embed(
                title="🔮 Résultat Akinator",
                description=f"Je pense que c'est : **{best_card['name']}** !" if best_card else "❌ Impossible de deviner...",
                color=discord.Color.purple()
            )
            if best_card and best_card.get("card_images"):
                embed.set_image(url=best_card["card_images"][0].get("image_url", ""))
            await safe_edit(interaction.message if interaction else self.message, embed=embed, view=None)
            return

        # Choisir question
        q = self.choose_best_question()
        if not q:
            # Aucune question restante
            embed = discord.Embed(
                title="❌ Fin des questions",
                description="Je n'ai plus de questions pour affiner la recherche.",
                color=discord.Color.red()
            )
            await safe_edit(interaction.message if interaction else self.message, embed=embed, view=None)
            return

        self.current_question = q
        self.asked_questions.add(q["filter_key"])
        question_text = q.get("text", "…").replace("{value}", q.get("filter_value", ["…"])[0])

        embed = discord.Embed(
            title="❓ Question Akinator",
            description=f"{question_text}\n\n({len(self.cards)} cartes en jeu)",
            color=discord.Color.blue()
        )

        self.clear_items()
        for label in ["Oui", "Non", "Ne sais pas", "Abandonner"]:
            style = discord.ButtonStyle.danger if label == "Abandonner" else discord.ButtonStyle.primary
            self.add_item(AkinatorButton(self, label, style))

        await safe_edit(interaction.message if interaction else self.message, embed=embed, view=self)

    # 🔹 Traiter réponse
    async def process_answer(self, answer, interaction: discord.Interaction):
        if answer == "Abandonner":
            embed = discord.Embed(
                title="🛑 Partie arrêtée",
                description="Tu as abandonné l'Akinator.",
                color=discord.Color.red()
            )
            await safe_edit(interaction.message, embed=embed, view=None)
            return

        # Mettre à jour probabilités
        key = self.current_question.get("filter_key")
        values = self.current_question.get("filter_value", [])
        for c in self.cards:
            c_values = c.get(key, [])
            id_ = c["id"]
            if answer == "Oui":
                if any(v in c_values for v in values):
                    self.probabilities[id_] *= 1.2
                else:
                    self.probabilities[id_] *= 0.5
            elif answer == "Non":
                if any(v in c_values for v in values):
                    self.probabilities[id_] *= 0.5
                else:
                    self.probabilities[id_] *= 1.2
            elif answer == "Ne sais pas":
                self.probabilities[id_] *= 1.0  # pas de changement

        # Normaliser
        total_prob = sum(self.probabilities.values())
        for k in self.probabilities:
            self.probabilities[k] /= total_prob

        self.question_count += 1
        await self.ask_question(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🔘 Boutons
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorButton(Button):
    def __init__(self, view, label, style=discord.ButtonStyle.primary):
        super().__init__(label=label, style=style)
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        await self.view.process_answer(self.label, interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Akinator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_random_cards(self, limit=150):
        safe_limit = min(limit, 150)
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"[ERREUR] HTTP {resp.status}")
                    return []
                data = await resp.json()

        all_cards = data.get("data", [])
        if not all_cards:
            return []

        sampled = random.sample(all_cards, min(safe_limit, len(all_cards)))
        cards = []
        for c in sampled:
            cards.append({
                "id": c.get("id"),
                "name": c.get("name", "Inconnue"),
                "type_subtype": (c.get("type", "") + " " + c.get("race", "")).split(),
                "attribute": [c.get("attribute")] if c.get("attribute") else [],
                "archetype": [c.get("archetype")] if c.get("archetype") else [],
                "effect": ["Effect"] if c.get("desc") and "effect" in c.get("desc").lower() else ["Normal"],
                "level": c.get("level", 0),
                "atk": c.get("atk", 0) or 0,
                "def": c.get("def", 0) or 0,
                "linkval": c.get("linkval", 0) or 0,
                "card_images": c.get("card_images", []),
            })
        return cards

    async def start_akinator(self, ctx_or_channel, interaction=None):
        questions = load_questions()
        if not questions:
            await safe_send(ctx_or_channel, "❌ Impossible de charger les questions.")
            return
        cards = await self.fetch_random_cards()
        if not cards:
            await safe_send(ctx_or_channel, "❌ Impossible de récupérer les cartes.")
            return
        view = AkinatorView(self.bot, questions, cards)
        embed = view.get_initial_embed_and_buttons()
        view.message = await safe_send(ctx_or_channel, embed=embed, view=view)

    @app_commands.command(name="akinator", description="Laisse Akinator deviner ta carte Yu-Gi-Oh!")
    async def slash_akinator(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.start_akinator(interaction)

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
