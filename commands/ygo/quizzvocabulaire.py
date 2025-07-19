# ────────────────────────────────────────────────────────────────────────────────
# 📌 vocabulaire.py — Commande interactive !vocabulaire
# Objectif : Quiz interactif sur le vocabulaire Yu-Gi-Oh!
# Catégorie : Yu-Gi-Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import random
import json
import os
from utils.discord_utils import safe_send, safe_edit, safe_respond  # ✅ Utilisation des safe_

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON (quiz vocabulaire)
# ────────────────────────────────────────────────────────────────────────────────
VOCAB_PATH = os.path.join("data", "vocabulaire.json")

def load_vocab_quiz():
    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue interactive du quiz
# ────────────────────────────────────────────────────────────────────────────────
class QuizButton(Button):
    def __init__(self, label, is_correct, view):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.is_correct = is_correct
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        for child in self.view.children:
            child.disabled = True
            if isinstance(child, QuizButton):
                if child.is_correct:
                    child.style = discord.ButtonStyle.success
                elif child.label == self.label:
                    child.style = discord.ButtonStyle.danger

        if self.is_correct:
            result = "✅ Bonne réponse !"
        else:
            result = "❌ Mauvaise réponse."

        await safe_edit(
            interaction.message,
            content=result,
            embed=None,
            view=self.view
        )
        self.view.stop()

class QuizView(View):
    def __init__(self, definition, choices, correct_answer):
        super().__init__(timeout=30)
        for choice in choices:
            is_correct = (choice == correct_answer)
            self.add_item(QuizButton(choice, is_correct, self))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Vocabulaire(commands.Cog):
    """
    Commande !vocabulaire — Quiz sur le vocabulaire Yu-Gi-Oh!
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="quizzvocabulaire", aliases=["qv"],
        help="Teste tes connaissances sur le vocabulaire Yu-Gi-Oh!",
        description="Affiche une définition et propose plusieurs termes au choix."
    )
    async def vocabulaire(self, ctx: commands.Context):
        """Commande principale de quiz vocabulaire."""
        try:
            data = load_vocab_quiz()
            question = random.choice(data)

            definition = question["definition"]
            correct = question["terme"]
            autres = question["autres"]
            options = autres + [correct]
            random.shuffle(options)

            embed = discord.Embed(
                title="🧠 Quiz Yu-Gi-Oh! — Vocabulaire",
                description=f"📘 **Définition :**\n{definition}",
                color=discord.Color.gold()
            )
            view = QuizView(definition, options, correct)

            await safe_send(ctx.channel, embed=embed, view=view)

        except Exception as e:
            print(f"[ERREUR vocabulaire] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors du chargement du quiz.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Vocabulaire(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Yu-Gi-Oh"
    await bot.add_cog(cog)
