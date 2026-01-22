# ────────────────────────────────────────────────────────────────────────────────
# 📌 mtgrandom.py
# Objectif : Affiche une carte Magic aléatoire depuis l'API Scryfall
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
class MTGRandom(commands.Cog):
    """
    Commande /mtgrandom et !mtgrandom — Affiche une carte Magic aléatoire
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
        name="mtgrandom",
        description="Affiche une carte Magic aléatoire."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mtgrandom(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.fetch_endpoint("/cards/random")
        if not data:
            await safe_respond(interaction, "❌ Impossible de récupérer une carte.")
            return

        embed = self.card_embed(data)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mtgrandom")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mtgrandom(self, ctx: commands.Context):
        data = await self.fetch_endpoint("/cards/random")
        if not data:
            await safe_send(ctx.channel, "❌ Impossible de récupérer une carte.")
            return

        embed = self.card_embed(data)
        await safe_send(ctx.channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🧩 Utilitaires API
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_endpoint(self, endpoint: str):
        session = self.bot.aiohttp_session  # ✅ On prend la session globale du bot
        async with session.get(f"{self.SCRYFALL}{endpoint}", headers=self.HEADERS) as r:
            return await r.json() if r.status == 200 else None


    def card_embed(self, data: dict) -> discord.Embed:
        embed = discord.Embed(
            title=data.get("name", "—"),
            description=data.get("oracle_text", "—"),
            color=discord.Color.purple()
        )

        embed.add_field(name="Mana", value=data.get("mana_cost", "—"), inline=True)
        embed.add_field(name="Type", value=data.get("type_line", "—"), inline=False)
        embed.add_field(name="Set", value=data.get("set_name", "—"), inline=True)
        embed.add_field(name="Rareté", value=data.get("rarity", "—").capitalize(), inline=True)

        if "image_uris" in data:
            embed.set_image(url=data["image_uris"].get("normal"))

        embed.set_footer(
            text=f"Illustration : {data.get('artist', '—')} • Source : Scryfall"
        )

        return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MTGRandom(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "MagicTCG"
    await bot.add_cog(cog)
