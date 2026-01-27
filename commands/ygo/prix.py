# ────────────────────────────────────────────────────────────────────────────────
# 📌 prix.py — Commande améliorée /prix et !prix
# Objectif :
#   - Affiche le prix d'une carte Yu-Gi-Oh! depuis l'API YGOPRODeck
#   - Recherche multi-langue, fallback aléatoire
#   - Utilise utils/card_utils pour la recherche
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond
from utils.card_utils import search_card, fetch_random_card  # ✅ Centralisé

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Helper de formatage
# ────────────────────────────────────────────────────────────────────────────────
def format_price(price: str, currency: str) -> str:
    try:
        return f"{currency}{float(price):.2f}"
    except (ValueError, TypeError):
        return "N/A"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Prix(commands.Cog):
    """Commande !prix — Affiche le prix d'une carte Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Fonction commune d'affichage ────────────────────────────────────────────
    async def send_price_embed(self, card: dict, ctx_or_interaction):
        prices = card.get("card_prices", [{}])[0]
        description = (
            f"💰 **Cardmarket** : {format_price(prices.get('cardmarket_price'), '€')}\n"
            f"💰 **TCGPlayer** : {format_price(prices.get('tcgplayer_price'), '$')}\n"
            f"💰 **eBay** : {format_price(prices.get('ebay_price'), '$')}\n"
            f"💰 **Amazon** : {format_price(prices.get('amazon_price'), '$')}\n"
            f"💰 **CoolStuffInc** : {format_price(prices.get('coolstuffinc_price'), '$')}"
        )

        embed = discord.Embed(
            title=f"📌 Prix de {card.get('name', 'Carte inconnue')}",
            description=description,
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=card.get("card_images", [{}])[0].get("image_url_small"))
        embed.set_footer(text=f"ID : {card.get('id', '?')} | Konami ID : {card.get('konami_id', '?')}")

        # Envoie du message (compatibilité interaction + message classique)
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.edit_original_response(embed=embed)
        else:
            await ctx_or_interaction.edit(content=None, embed=embed)

    
    # ── Commande slash
    @app_commands.command(
        name="prix",
        description="Affiche le prix d'une carte Yu-Gi-Oh!"
    )
    @app_commands.describe(carte="Nom exact de la carte")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_prix(self, interaction: discord.Interaction, carte: str):
        await safe_respond(interaction, f"🔄 Recherche du prix pour **{carte}**…")
    
        card, lang, message = await search_card(carte, self.bot.aiohttp_session)
        if message:
            return await safe_respond(interaction, message)
        if not card:
            card, lang = await fetch_random_card(self.bot.aiohttp_session)
            if not card:
                return await safe_respond(interaction, "❌ Carte introuvable.")
            await safe_respond(interaction, f"❌ Carte `{carte}` introuvable. 🔄 Voici une carte aléatoire à la place :")
    
        await self.send_price_embed(card, interaction)
    
    
    # ── Commande préfixe
    @commands.command(name="prix", help="Affiche le prix d'une carte Yu-Gi-Oh!")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_prix(self, ctx: commands.Context, *, carte: str):
        msg = await safe_send(ctx.channel, f"🔄 Recherche du prix pour **{carte}**…")
    
        card, lang, message = await search_card(carte, self.bot.aiohttp_session)
        if message:
            return await safe_send(ctx, message)
        if not card:
            card, lang = await fetch_random_card(self.bot.aiohttp_session)
            if not card:
                return await safe_send(ctx, "❌ Carte introuvable.")
            await safe_send(ctx, f"❌ Carte `{carte}` introuvable. 🔄 Voici une carte aléatoire à la place :")
    
        await self.send_price_embed(card, msg)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Prix(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
