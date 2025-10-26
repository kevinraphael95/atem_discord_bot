# ────────────────────────────────────────────────────────────────────────────────
# 📌 staples.py — Commande pour afficher les cartes Staples
# Objectif : Récupère et affiche les cartes considérées comme staples
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
import aiohttp
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Staples(commands.Cog):
    """Commande /staples et !staples — Liste des cartes Staples"""

    API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_staples(self):
        """Récupère les cartes staples depuis l'API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("data", [])

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="staples",
        description="Affiche une liste de cartes considérées comme staples."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_staples(self, interaction: discord.Interaction):
        """Commande slash pour afficher les staples"""
        await safe_respond(interaction, "🔄 Récupération des cartes…")
        staples = await self.fetch_staples()
        if not staples:
            return await safe_respond(interaction, "❌ Impossible de récupérer les cartes.")
        
        embed = discord.Embed(
            title="📌 Cartes Staples",
            description="\n".join(f"**{c['name']}** - {c['type']}" for c in staples[:10]),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Affichage des 10 premiers staples sur {len(staples)}")
        await interaction.edit_original_response(embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="staples")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_staples(self, ctx: commands.Context):
        """Commande préfixe pour afficher les staples"""
        msg = await safe_send(ctx.channel, "🔄 Récupération des cartes…")
        staples = await self.fetch_staples()
        if not staples:
            return await safe_send(ctx.channel, "❌ Impossible de récupérer les cartes.")

        embed = discord.Embed(
            title="📌 Cartes Staples",
            description="\n".join(f"**{c['name']}** - {c['type']}" for c in staples[:10]),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Affichage des 10 premiers staples sur {len(staples)}")
        await msg.edit(content=None, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Staples(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Autre"
    await bot.add_cog(cog)
