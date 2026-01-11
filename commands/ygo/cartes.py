# ────────────────────────────────────────────────────────────────────────────────
# 📌 cartes.py — Affiche un embed avec liens vers des projets de cartes custom Yu-Gi-Oh!
# Objectif : Partager plusieurs projets GitHub via boutons
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🔘 View avec boutons
# ────────────────────────────────────────────────────────────────────────────────
class CartesCustomView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="VA-ACT Custom YGO",
                style=discord.ButtonStyle.link,
                url="https://github.com/kevinraphael95/vaact_custom_ygo"
            )
        )

        self.add_item(
            discord.ui.Button(
                label="Dark Souls YGO",
                style=discord.ButtonStyle.link,
                url="https://github.com/kevinraphael95/darksoulsygo"
            )
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CartesCustom(commands.Cog):
    """
    Commande /cartes et !cartes — Affiche un embed avec plusieurs projets de cartes custom
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="cartes",
        description="Affiche les projets de cartes custom Yu-Gi-Oh!"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_cartes(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🃏 Cartes custom Yu-Gi-Oh!",
            description=(
                "Voici différents projets de **cartes Yu-Gi-Oh! custom**.\n"
                "Clique sur les boutons ci-dessous pour découvrir les univers 👇"
            ),
            color=discord.Color.blue()
        )

        await safe_respond(
            interaction,
            embed=embed,
            view=CartesCustomView()
        )

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="cartes")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_cartes(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🃏 Cartes custom Yu-Gi-Oh!",
            description=(
                "Voici différents projets de **cartes Yu-Gi-Oh! custom**.\n"
                "Clique sur les boutons ci-dessous pour découvrir les univers 👇"
            ),
            color=discord.Color.blue()
        )

        await safe_send(
            ctx.channel,
            embed=embed,
            view=CartesCustomView()
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CartesCustom(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
