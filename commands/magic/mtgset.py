# ────────────────────────────────────────────────────────────────────────────────
# 📌 mtgset.py
# Objectif : Affiche les informations d'un set Magic depuis l'API Scryfall
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
class MTGSet(commands.Cog):
    """
    Commande /mtgset et !mtgset — Affiche les informations d'un set Magic
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
        name="mtgset",
        description="Affiche les informations d'un set Magic."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mtgset(self, interaction: discord.Interaction, set_code: str):
        await interaction.response.defer()
        data = await self.fetch_endpoint(f"/sets/{set_code.lower()}")
        if not data:
            await safe_respond(interaction, "❌ Set introuvable.")
            return

        embed = discord.Embed(
            title=data.get("name", "—"),
            description=f"Code : `{data.get('code', '—').upper()}`",
            color=discord.Color.gold()
        )
        embed.add_field(name="Type", value=data.get("set_type", "—"), inline=True)
        embed.add_field(name="Cartes", value=data.get("card_count", "—"), inline=True)
        embed.add_field(name="Sortie", value=data.get("released_at", "—"), inline=True)
        embed.set_footer(text="Source : Scryfall")

        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mtgset")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mtgset(self, ctx: commands.Context, set_code: str):
        data = await self.fetch_endpoint(f"/sets/{set_code.lower()}")
        if not data:
            await safe_send(ctx.channel, "❌ Set introuvable.")
            return

        embed = discord.Embed(
            title=data.get("name", "—"),
            description=f"Code : `{data.get('code', '—').upper()}`",
            color=discord.Color.gold()
        )
        embed.add_field(name="Type", value=data.get("set_type", "—"), inline=True)
        embed.add_field(name="Cartes", value=data.get("card_count", "—"), inline=True)
        embed.add_field(name="Sortie", value=data.get("released_at", "—"), inline=True)
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
    cog = MTGSet(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "MagicTCG"
    await bot.add_cog(cog)
