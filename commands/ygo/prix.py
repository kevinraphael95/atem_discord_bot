# ────────────────────────────────────────────────────────────────────────────────
# 📌 prix.py — Commande améliorée /prix et !prix
# Objectif : Affiche le prix d'une carte Yu-Gi-Oh! depuis l'API YGOPRODeck
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import urllib.parse
from utils.discord_utils import safe_send, safe_respond

BASE_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Helpers
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_card_multilang(name: str):
    """Recherche multi-langue (fr, de, it, pt, en)"""
    name_encode = urllib.parse.quote(name)
    languages = ["fr", "de", "it", "pt", ""]
    async with aiohttp.ClientSession() as session:
        for lang in languages:
            url = f"{BASE_URL}?name={name_encode}"
            if lang:
                url += f"&language={lang}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        return data["data"][0], (lang or "en")
    return None, "?"

async def fetch_random_card():
    """Récupère une carte aléatoire"""
    async with aiohttp.ClientSession() as session:
        for lang in ["fr", "en"]:
            async with session.get(f"https://db.ygoprodeck.com/api/v7/randomcard.php?language={lang}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data:
                        return data["data"][0], lang
    return None, "?"

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

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.edit_original_response(embed=embed)
        else:
            await ctx_or_interaction.edit(content=None, embed=embed)

    # ── Commande slash ─────────────────────────────────────────────────────────
    @app_commands.command(
        name="prix",
        description="Affiche le prix d'une carte Yu-Gi-Oh!"
    )
    @app_commands.describe(carte="Nom exact de la carte")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_prix(self, interaction: discord.Interaction, carte: str):
        await safe_respond(interaction, f"🔄 Recherche du prix pour **{carte}**…")
        card, lang = await fetch_card_multilang(carte)
        if not card:
            card, lang = await fetch_random_card()
            if not card:
                return await safe_respond(interaction, "❌ Carte introuvable.")
            await safe_respond(interaction, f"❌ Carte `{carte}` introuvable. 🔄 Voici une carte aléatoire à la place :")
        await self.send_price_embed(card, interaction)

    # ── Commande préfixe ───────────────────────────────────────────────────────
    @commands.command(name="prix")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_prix(self, ctx: commands.Context, *, carte: str):
        msg = await safe_send(ctx.channel, f"🔄 Recherche du prix pour **{carte}**…")
        card, lang = await fetch_card_multilang(carte)
        if not card:
            card, lang = await fetch_random_card()
            if not card:
                return await safe_send(ctx.channel, "❌ Carte introuvable.")
            await safe_send(ctx.channel, f"❌ Carte `{carte}` introuvable. 🔄 Voici une carte aléatoire à la place :")
        await self.send_price_embed(card, msg)

# ── Setup du Cog ─────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Prix(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
