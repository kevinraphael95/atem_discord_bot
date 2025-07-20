# ────────────────────────────────────────────────────────────────────────────────
# 📌 true_false.py — Commande interactive !vraioufaux avec boutons Vrai/Faux
# Objectif : Mini-quiz interactif Vrai ou Faux sur Yu-Gi-Oh!
# Catégorie : Fun / Apprentissage / Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import random
from utils.discord_utils import safe_send, safe_edit  # Utilisation des safe_

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des questions depuis JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "vof.json")

def load_questions():
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View interactive avec boutons Vrai / Faux
# ────────────────────────────────────────────────────────────────────────────────
class TrueFalseView(View):
    def __init__(self, ctx, statement, answer):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.statement = statement
        self.answer = answer
        self.answered = False

    @discord.ui.button(label="Vrai", style=discord.ButtonStyle.green)
    async def true_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("❌ Ce n'est pas ton quiz !", ephemeral=True)
        if self.answered:
            return await interaction.response.defer()
        self.answered = True

        if self.answer is True:
            await interaction.response.send_message("✅ Correct !", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Faux !", ephemeral=True)

    @discord.ui.button(label="Faux", style=discord.ButtonStyle.red)
    async def false_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("❌ Ce n'est pas ton quiz !", ephemeral=True)
        if self.answered:
            return await interaction.response.defer()
        self.answered = True

        if self.answer is False:
            await interaction.response.send_message("✅ Correct !", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Faux !", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TrueFalse(commands.Cog):
    """
    Commande !vraioufaux — Quiz Vrai ou Faux interactif
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.questions = load_questions()

    @commands.command(
        name="vraioufaux", aliases=["vof"],
        help="Lance un quiz Vrai ou Faux sur Yu-Gi-Oh!",
        description="Pose une question Vrai ou Faux avec boutons interactifs."
    )
    async def vrai_ou_faux(self, ctx: commands.Context):
        question = self.questions[random.randint(0, len(self.questions) - 1)]

        embed = discord.Embed(
            title="🃏 Quiz Yu-Gi-Oh! : Vrai ou Faux ?",
            description=question["statement"],
            color=discord.Color.blue()
        )

        view = TrueFalseView(ctx, question["statement"], question["answer"])
        await safe_send(ctx.channel, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TrueFalse(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
