# ────────────────────────────────────────────────────────────────────────────────
# 📌 quizzvocabulaire.py
# Objectif : Quiz interactif sur le vocabulaire Yu-Gi-Oh! (définition + choix)
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 5 secondes par utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import random
from typing import List
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON (vocabulaire)
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "vocabulaire.json")

def load_vocabulaire():
    """Charge le fichier JSON contenant les termes du vocabulaire."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {DATA_JSON_PATH} : {e}")
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton de réponse
# ────────────────────────────────────────────────────────────────────────────────
class AnswerButton(Button):
    def __init__(self, label: str, correct_answer: str, parent_view: "QuizView"):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.correct_answer = correct_answer
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if self.disabled:
            return
        self.parent_view.disable_all_items()
        await interaction.response.edit_message(view=self.parent_view)
        if self.label == self.correct_answer:
            response = f"✅ Bravo ! **{self.label}** est la bonne réponse."
        else:
            response = f"❌ Mauvaise réponse... La bonne réponse était **{self.correct_answer}**."
        await safe_send(interaction.channel, response)
        self.parent_view.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue du quiz
# ────────────────────────────────────────────────────────────────────────────────
class QuizView(View):
    def __init__(self, options_list: List[str], correct_answer: str):
        super().__init__(timeout=60)
        for opt in options_list:
            self.add_item(AnswerButton(label=opt, correct_answer=correct_answer, parent_view=self))

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec commandes prefix et slash
# ────────────────────────────────────────────────────────────────────────────────
class QuizzVocabulaire(commands.Cog):
    """Commande !quizzvocabulaire et /quizzvocabulaire — Quiz interactif sur le vocabulaire Yu-Gi-Oh!"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.vocabulaire = load_vocabulaire()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour lancer le quiz
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_quiz(self, channel: discord.abc.Messageable):
        try:
            if len(self.vocabulaire) < 4:
                raise ValueError("Pas assez de données pour lancer un quiz.")

            terme, infos = random.choice(list(self.vocabulaire.items()))
            definition = infos.get("definition", "Définition indisponible.")

            autres_termes = [k for k in self.vocabulaire.keys() if k != terme]
            choix = random.sample(autres_termes, k=3)
            choix.append(terme)
            random.shuffle(choix)

            embed = discord.Embed(
                title="📘 Quizz Vocabulaire Yu-Gi-Oh!",
                description=f"**Définition :**\n{definition}\n\nClique sur le bon terme :",
                color=discord.Color.dark_orange()
            )
            view = QuizView(choix, terme)
            await safe_send(channel, embed=embed, view=view)

        except Exception as e:
            print(f"[ERREUR quizzvocabulaire] {e}")
            await safe_send(channel, f"❌ Une erreur est survenue : `{e}`")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="quizzvocabulaire", aliases=["qv"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_quizzvocabulaire(self, ctx: commands.Context):
        await self._start_quiz(ctx.channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="quizzvocabulaire", description="Fais un quiz interactif sur le vocabulaire Yu-Gi-Oh!")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_quizzvocabulaire(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_quiz(interaction.channel)
        await interaction.delete_original_response()

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = QuizzVocabulaire(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
