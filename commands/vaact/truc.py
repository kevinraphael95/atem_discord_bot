# ────────────────────────────────────────────────────────────────────────────────
# 📌 truc.py — Affiche un embed avec lien vers VA-ACT Custom Yu-Gi-Oh!
# Objectif : Commande simple pour partager le lien GitHub et un texte
# Catégorie : Autre
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
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TestCarteCustom(commands.Cog):
    """
    Commande /test_carte_custom et !test_carte_custom — Affiche un embed avec lien et texte
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="truc",
        description="Affiche un embed avec le lien et un petit texte."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_test_carte_custom(self, interaction: discord.Interaction):
        """Commande slash sécurisée"""
        embed = discord.Embed(
            title="Test cartes custom Yu-Gi-Oh! VAACT",
            description="Voici le lien vers le dépôt GitHub avec toutes les cartes custom Yu-Gi-Oh!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Lien GitHub",
            value="[VA-ACT Custom YGO](https://github.com/kevinraphael95/vaact_custom_ygo/blob/main/README.md)",
            inline=False
        )
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="truc")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_test_carte_custom(self, ctx: commands.Context):
        """Commande préfixe sécurisée"""
        embed = discord.Embed(
            title="Test cartes custom Yu-Gi-Oh! VAACT",
            description="Voici le lien vers le dépôt GitHub avec toutes les cartes custom Yu-Gi-Oh!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Lien GitHub",
            value="[VA-ACT Custom YGO](https://github.com/kevinraphael95/vaact_custom_ygo/blob/main/README.md)",
            inline=False
        )
        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestCarteCustom(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
