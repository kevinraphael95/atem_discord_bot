# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact_ygo.py — Commande /vaact_ygo et !vaact_ygo
# Objectif : Fournir le lien vers le README du projet Vaact Custom YGO
# Catégorie : VAACT
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
class VaactYGO(commands.Cog):
    """
    Commande /vaact_ygo et !vaact_ygo — Lien vers les cartes custom Vaact
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    README_URL = "https://github.com/kevinraphael95/vaact_custom_ygo/blob/main/README.md"

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="vaact_ygo",
        description="Affiche le lien vers les cartes et decks custom VAACT."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_vaact_ygo(self, interaction: discord.Interaction):
        """Retourne le lien du README — version SLASH"""
        embed = discord.Embed(
            title="🃏 Cartes et Decks custom VAACT",
            description=f"[📘 Cliquez ici pour accéder au README]({self.README_URL})",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Projet Custom YGO — Kal & Angel")
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="vaact_ygo")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_vaact_ygo(self, ctx: commands.Context):
        """Retourne le lien du README — version PREFIX (!vaact_ygo)"""
        embed = discord.Embed(
            title="🃏 Cartes et Decks custom VAACT",
            description=f"[📘 Cliquez ici pour accéder au README]({self.README_URL})",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Projet Custom YGO — Kal & Angel")
        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = VaactYGO(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
