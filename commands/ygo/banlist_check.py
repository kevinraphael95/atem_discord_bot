# ────────────────────────────────────────────────────────────────────────────────
# 📌 banlist_check.py
# Objectif : Vérifier le statut banlist (TCG / OCG / GOAT) d'une carte Yu-Gi-Oh!
# Catégorie : Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

from utils.discord_utils import safe_send

API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class BanlistCheck(commands.Cog):
    """
    Commande /banlist_check et !banlist_check — Vérifie la banlist d'une carte
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne
    # ────────────────────────────────────────────────────────────────────────────
    async def _fetch_card(self, name: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params={"name": name}) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data["data"][0]

    async def _send_result(self, channel, name: str):
        card = await self._fetch_card(name)
        if not card:
            await safe_send(channel, "❌ Carte introuvable.")
            return

        ban = card.get("banlist_info", {})
        embed = discord.Embed(
            title=f"📜 Banlist — {card['name']}",
            color=discord.Color.red()
        )
        embed.add_field(name="TCG", value=ban.get("ban_tcg", "Autorisé"), inline=True)
        embed.add_field(name="OCG", value=ban.get("ban_ocg", "Autorisé"), inline=True)
        embed.add_field(name="GOAT", value=ban.get("ban_goat", "Autorisé"), inline=True)

        await safe_send(channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="banlist_check",
        description="Vérifie le statut banlist d'une carte Yu-Gi-Oh!"
    )
    @app_commands.describe(carte="Nom exact de la carte")
    @app_commands.checks.cooldown(1, 5.0)
    async def slash_banlist_check(self, interaction: discord.Interaction, carte: str):
        await interaction.response.defer()
        await self._send_result(interaction.channel, carte)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="banlist_check")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_banlist_check(self, ctx: commands.Context, *, carte: str):
        await self._send_result(ctx.channel, carte)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog (CONFORME TEMPLATE)
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = BanlistCheck(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Yu-Gi-Oh!"
    await bot.add_cog(cog)
