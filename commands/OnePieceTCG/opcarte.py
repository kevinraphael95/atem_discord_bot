# ────────────────────────────────────────────────────────────────────────────────
# 📌 opcarte.py — Commande /opcarte et !opcarte
# Objectif :
#   - Afficher une carte One Piece TCG
#   - Recherche par nom (EN / JP)
#   - Embed propre avec image, stats et effet
# Catégorie : One Piece TCG
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 API One Piece TCG
# ────────────────────────────────────────────────────────────────────────────────
OPTCG_API = "https://onepiece-cardgame.dev/api/cards"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class OPCarte(commands.Cog):
    """
    Commande /opcarte et !opcarte — Affiche une carte One Piece TCG
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Recherche carte
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_card(self, name: str) -> dict | None:
        session = self.bot.aiohttp_session

        async with session.get(OPTCG_API, params={"search": name}) as resp:
            if resp.status != 200:
                return None

            data = await resp.json()
            cards = data.get("data", [])
            return cards[0] if cards else None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Embed carte
    # ────────────────────────────────────────────────────────────────────────────
    def build_card_embed(self, card: dict) -> discord.Embed:
        name = card.get("name", "Carte inconnue")
        card_type = card.get("type", "—")
        effect = card.get("effect", "—")
        color = card.get("color", [])
        cost = card.get("cost")
        power = card.get("power")
        counter = card.get("counter")
        rarity = card.get("rarity")
        set_code = card.get("set")

        embed = discord.Embed(
            title=f"🃏 {name}",
            description=f"**Effet**\n{effect}",
            color=discord.Color.red()
        )

        embed.add_field(name="Type", value=card_type, inline=True)
        if cost is not None:
            embed.add_field(name="Coût", value=f"{cost}", inline=True)
        if power:
            embed.add_field(name="Puissance", value=f"{power}", inline=True)
        if counter:
            embed.add_field(name="Counter", value=f"+{counter}", inline=True)

        if color:
            embed.add_field(name="Couleur", value=", ".join(color), inline=True)
        if rarity:
            embed.add_field(name="Rareté", value=rarity, inline=True)
        if set_code:
            embed.add_field(name="Set", value=set_code, inline=True)

        image = card.get("image")
        if image:
            embed.set_image(url=image)

        embed.set_footer(text="Source : One Piece Card Game API")

        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="opcarte",
        description="Affiche une carte One Piece TCG"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_opcarte(
        self,
        interaction: discord.Interaction,
        nom: str
    ):
        await interaction.response.defer()

        card = await self.fetch_card(nom)
        if not card:
            await safe_respond(interaction, "❌ Carte introuvable.")
            return

        embed = self.build_card_embed(card)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="opcarte")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_opcarte(self, ctx: commands.Context, *, nom: str):
        card = await self.fetch_card(nom)
        if not card:
            await safe_send(ctx.channel, "❌ Carte introuvable.")
            return

        embed = self.build_card_embed(card)
        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = OPCarte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "One Piece TCG"
    await bot.add_cog(cog)
