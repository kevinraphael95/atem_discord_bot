# ────────────────────────────────────────────────────────────────────────────────
# 📌 quizzvocabulaire.py — Commande interactive !quizzvocabulaire
# Objectif : Quiz interactif sur le vocabulaire Yu-Gi-Oh! (définition + choix)
# Catégorie : Yu-Gi-Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────
# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Select
import json
import os
from utils.discord_utils import safe_send, safe_edit, safe_respond  # ✅ Utilisation des safe_
# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON (vocabulaire)
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "vocabulaire.json")

def load_vocabulaire():
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Menu du quiz (select des réponses)
# ────────────────────────────────────────────────────────────────────────────────
class QuizSelect(Select):
    def __init__(self, parent_view: "QuizView", options_list: list[str], correct_answer: str):
        self.parent_view = parent_view
        self.correct_answer = correct_answer
        select_options = [discord.SelectOption(label=opt, value=opt) for opt in options_list]
        super().__init__(placeholder="Choisis la bonne réponse", options=select_options, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == self.correct_answer:
            content = f"✅ Bravo ! **{selected}** est la bonne réponse."
        else:
            content = f"❌ Mauvaise réponse... La bonne réponse était **{self.correct_answer}**."
        # Disable select after réponse
        self.parent_view.clear_items()
        await safe_edit(interaction.message, content=content, embed=None, view=None)
        self.parent_view.stop()
# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue du quiz
# ────────────────────────────────────────────────────────────────────────────────
class QuizView(View):
    def __init__(self, bot, question: str, options_list: list[str], correct_answer: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.question = question
        self.add_item(QuizSelect(self, options_list, correct_answer))
# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class QuizzVocabulaire(commands.Cog):
    """
    Commande !quizzvocabulaire — Quiz interactif sur le vocabulaire Yu-Gi-Oh!
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.vocabulaire = load_vocabulaire()

    @commands.command(
        name="quizzvocabulaire",
        help="Fais un quiz interactif sur le vocabulaire Yu-Gi-Oh!",
        description="Donne une définition et propose 4 termes, trouve le bon."
    )
    async def quizzvocabulaire(self, ctx: commands.Context):
        """Commande principale avec menu interactif de quiz."""
        try:
            import random
            terme, infos = random.choice(list(self.vocabulaire.items()))
            definition = infos.get("definition", "Définition indisponible.")
            # Construction des options (1 bonne réponse + 3 aléatoires)
            autres_termes = list(self.vocabulaire.keys())
            autres_termes.remove(terme)
            choix = random.sample(autres_termes, k=3)
            choix.append(terme)
            random.shuffle(choix)
            embed = discord.Embed(
                title="Quizz Vocabulaire Yu-Gi-Oh!",
                description=f"**Définition :**\n{definition}\n\nSélectionne le terme correspondant :",
                color=discord.Color.dark_orange()
            )
            view = QuizView(self.bot, definition, choix, terme)
            await safe_send(ctx.channel, embed=embed, view=view)
        except Exception as e:
            print(f"[ERREUR quizzvocabulaire] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors du lancement du quiz.")
# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = QuizzVocabulaire(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Yu-Gi-Oh"
    await bot.add_cog(cog)
