# ────────────────────────────────────────────────────────────────────────────────
# 🎲 Random.py — Commande !random
# Objectif : Tirer une carte Yu-Gi-Oh! aléatoire et l'afficher joliment dans un embed
# Source : API publique YGOPRODeck (https://db.ygoprodeck.com/api-guide/)
# Langue : 🇫🇷 Français uniquement
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import random

from utils.discord_utils import safe_send  # ✅ Protection anti 429

# ────────────────────────────────────────────────────────────────────────────────
# 📘 Classe principale du Cog de commande !random
# ────────────────────────────────────────────────────────────────────────────────
class Random(commands.Cog):
    """
    🎲 Cog de la commande !random : tire une carte Yu-Gi-Oh! aléatoire via l'API officielle.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot  # 🔗 Référence au bot principal

    # ────────────────────────────────────────────────────────────────────────────
    # 🎯 Commande principale !random
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="random",
        aliases=["aléatoire", "ran"],
        help="🎲 Affiche une carte Yu-Gi-Oh! aléatoire."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def random_card(self, ctx: commands.Context):
        """
        📥 Récupère une carte Yu-Gi-Oh! aléatoire depuis l’API (langue : français)
        et l'affiche joliment dans un embed Discord.
        """
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await safe_send(ctx, "❌ Erreur lors de l'accès à l'API.")
                    return
                data = await resp.json()

        if "data" not in data:
            await safe_send(ctx, "❌ Données invalides reçues depuis l’API.")
            return

        carte = random.choice(data["data"])

        embed = discord.Embed(
            title=carte["name"],
            description=carte.get("desc", "Pas de description disponible."),
            color=discord.Color.gold()
        )

        embed.set_author(
            name="Carte aléatoire Yu-Gi-Oh!",
            icon_url="https://cdn-icons-png.flaticon.com/512/361/361678.png"
        )

        embed.add_field(name="🧪 Type", value=carte.get("type", "—"), inline=True)

        if carte.get("type", "").lower().startswith("monstre"):
            embed.add_field(
                name="⚔️ ATK / DEF",
                value=f"{carte.get('atk', '—')} / {carte.get('def', '—')}",
                inline=True
            )
            embed.add_field(
                name="⭐ Niveau / Rang",
                value=str(carte.get("level", "—")),
                inline=True
            )
            embed.add_field(
                name="🌪️ Attribut",
                value=carte.get("attribute", "—"),
                inline=True
            )
            embed.add_field(
                name="👹 Race",
                value=carte.get("race", "—"),
                inline=True
            )

        image_url = carte.get("card_images", [{}])[0].get("image_url")
        if image_url:
            embed.set_thumbnail(url=image_url)

        await safe_send(ctx, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Fonction de setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    """
    🔧 Fonction appelée par Discord pour charger le Cog dans le bot.
    Permet d’ajouter les commandes dans la catégorie "🃏 Yu-Gi-Oh!".
    """
    cog = Random(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
