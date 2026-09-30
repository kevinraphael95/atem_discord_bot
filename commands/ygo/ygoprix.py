# ================================================================================
# 📌 prix.py — Commande améliorée /ygoprix et !ygoprix
# Objectif :
#   - Affiche le prix d'une carte Yu-Gi-Oh! depuis l'API YGOPRODeck
#   - Recherche par nom, fallback aléatoire
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Version optimisée : 1 appel API (fetch_card_full) + safe_defer
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import (
    safe_send, safe_defer, safe_followup, safe_edit_original
)
from utils.card_utils import fetch_card_full, fetch_random_card

# ================================================================================
# 🔧 Helper de formatage
# ================================================================================
def format_price(price: str, currency: str) -> str:
    try:
        return f"{currency}{float(price):.2f}"
    except (ValueError, TypeError):
        return "N/A"

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Prix(commands.Cog):
    """Commande /ygoprix et !ygoprix — Affiche le prix d'une carte Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # == Construction de l'embed =================================================
    def build_price_embed(self, card: dict) -> discord.Embed:
        prices = card.get("card_prices", [{}])[0]
        description = (
            f"💰 **Cardmarket** : {format_price(prices.get('cardmarket_price'), '€')}\n"
            f"💰 **TCGPlayer** : {format_price(prices.get('tcgplayer_price'), '$')}\n"
            f"💰 **eBay** : {format_price(prices.get('ebay_price'), '$')}\n"
            f"💰 **Amazon** : {format_price(prices.get('amazon_price'), '$')}\n"
            f"💰 **CoolStuffInc** : {format_price(prices.get('coolstuffinc_price'), '$')}"
        )

        embed = discord.Embed(
            title=f"📌 Prix de {card.get('name_fr') or card.get('name', 'Carte inconnue')}",
            description=description,
            color=discord.Color.gold()
        )

        if card.get("card_images"):
            embed.set_thumbnail(url=card["card_images"][0].get("image_url_small"))

        embed.set_footer(text=f"ID : {card.get('id', '?')} | Konami ID : {card.get('konami_id', '?')}")
        return embed

    # == Récupération de la carte (avec fallback aléatoire) ======================
    async def _fetch_card_with_fallback(self, nom: str, session):
        """Cherche la carte par nom, fallback aléatoire si introuvable."""
        card = await fetch_card_full(nom, session)
        if card:
            return card, False  # (card, is_fallback)
        # Fallback : carte aléatoire
        card, _ = await fetch_random_card(session)
        return card, True

    # == Commande SLASH ==========================================================
    @app_commands.command(
        name="ygoprix",
        description="Affiche le prix d'une carte Yu-Gi-Oh!"
    )
    @app_commands.describe(carte="Nom exact de la carte")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_prix(self, interaction: discord.Interaction, carte: str):
        # ✅ Defer sécurisé
        if not await safe_defer(interaction):
            return

        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return await safe_followup(interaction, "❌ Session HTTP non disponible.", ephemeral=True)

        card, is_fallback = await self._fetch_card_with_fallback(carte, session)
        if not card:
            return await safe_followup(interaction, "❌ Carte introuvable.", ephemeral=True)

        if is_fallback:
            await safe_followup(
                interaction,
                f"❌ Carte `{carte}` introuvable. 🔄 Voici une carte aléatoire à la place :"
            )

        embed = self.build_price_embed(card)
        await safe_edit_original(interaction, embed=embed)

    # == Commande PREFIX =========================================================
    @commands.command(name="ygoprix", aliases=["yprix"], help="Affiche le prix d'une carte Yu-Gi-Oh!")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_prix(self, ctx: commands.Context, *, carte: str):
        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return await safe_send(ctx.channel, "❌ Session HTTP non disponible.")

        card, is_fallback = await self._fetch_card_with_fallback(carte, session)
        if not card:
            return await safe_send(ctx.channel, "❌ Carte introuvable.")

        if is_fallback:
            await safe_send(
                ctx.channel,
                f"❌ Carte `{carte}` introuvable. 🔄 Voici une carte aléatoire à la place :"
            )

        embed = self.build_price_embed(card)
        await safe_send(ctx.channel, embed=embed)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Prix(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
