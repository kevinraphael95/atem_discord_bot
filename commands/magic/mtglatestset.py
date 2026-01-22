# ────────────────────────────────────────────────────────────────────────────────
# 📌 mtglatestset.py
# Objectif : Affiche le dernier set Magic sorti depuis l'API Scryfall
# Catégorie : MagicTCG
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

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_delete  

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MTGLatestSet(commands.Cog):
    """
    Commande /mtglatestset et !mtglatestset — Affiche le dernier set Magic sorti
    """
    SCRYFALL = "https://api.scryfall.com"
    HEADERS = {
        "User-Agent": "VaactMagicBot/1.0",
        "Accept": "application/json"
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtglatestset",
        description="Affiche le dernier set Magic sorti."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mtglatestset(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.fetch_endpoint("/sets")
        if not data or "data" not in data:
            await safe_respond(interaction, "❌ Impossible de récupérer les sets.")
            return

        latest = max((s for s in data["data"] if s.get("released_at")), key=lambda x: x["released_at"])

        embed = discord.Embed(
            title=latest.get("name", "—"),
            description=f"Code : `{latest.get('code', '—').upper()}`",
            color=discord.Color.green()
        )
        embed.add_field(name="Sortie", value=latest.get("released_at", "—"), inline=True)
        embed.add_field(name="Cartes", value=latest.get("card_count", "—"), inline=True)
        embed.set_footer(text="Source : Scryfall")

        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mtglatestset")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mtglatestset(self, ctx: commands.Context):
        data = await self.fetch_endpoint("/sets")
        if not data or "data" not in data:
            await safe_send(ctx.channel, "❌ Impossible de récupérer les sets.")
            return

        latest = max((s for s in data["data"] if s.get("released_at")), key=lambda x: x["released_at"])

        embed = discord.Embed(
            title=latest.get("name", "—"),
            description=f"Code : `{latest.get('code', '—').upper()}`",
            color=discord.Color.green()
        )
        embed.add_field(name="Sortie", value=latest.get("released_at", "—"), inline=True)
        embed.add_field(name="Cartes", value=latest.get("card_count", "—"), inline=True)
        embed.set_footer(text="Source : Scryfall")

        await safe_send(ctx.channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🧩 Utilitaires API
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_endpoint(self, endpoint: str):
        async with aiohttp.ClientSession(headers=self.HEADERS) as session:
            async with session.get(f"{self.SCRYFALL}{endpoint}") as r:
                return await r.json() if r.status == 200 else None

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MTGLatestSet(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "MagicTCG"
    await bot.add_cog(cog)
