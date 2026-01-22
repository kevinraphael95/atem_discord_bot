# ────────────────────────────────────────────────────────────────────────────────
# 📌 mtgcarte.py — Commande /mtgcarte et !mtgcarte
# Objectif : Afficher une carte Magic: The Gathering via Scryfall
# Catégorie : MagicTCG
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import aiohttp
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Constantes Scryfall
# ────────────────────────────────────────────────────────────────────────────────
SCRYFALL_API = "https://api.scryfall.com"

HEADERS = {
    "User-Agent": "VaactMagicBot/1.0",
    "Accept": "application/json"
}

LANGUAGES = [
    "en", "fr", "de", "es", "it", "pt", "jp", "kr", "zhs", "zht",
    "he", "la", "grc", "ar", "sa", "ph", "qya"
]

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MTGCarte(commands.Cog):
    """
    Commande /mtgcarte et !mtgcarte — Affiche une carte Magic
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Utilitaire API
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_card(self, name: str, lang: str = "en") -> dict | None:
        """Récupère une carte Magic depuis Scryfall dans la langue demandée."""
        if lang not in LANGUAGES:
            lang = "en"
        session = self.bot.aiohttp_session

        async with session.get(
            f"{SCRYFALL_API}/cards/named",
            params={"fuzzy": name, "lang": lang},
            headers=HEADERS
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Création de l'embed carte
    # ────────────────────────────────────────────────────────────────────────────
    def build_card_embed(self, data: dict) -> discord.Embed:
        name = data.get("printed_name") or data.get("name")
        type_line = data.get("printed_type_line") or data.get("type_line")
        text = data.get("printed_text") or data.get("oracle_text")

        embed = discord.Embed(
            title=name,
            description=text or "—",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Mana",
            value=data.get("mana_cost", "—"),
            inline=True
        )
        embed.add_field(
            name="Type",
            value=type_line or "—",
            inline=False
        )
        embed.add_field(
            name="Set",
            value=f"{data.get('set_name', '—')} ({data.get('set', '').upper()})",
            inline=True
        )
        embed.add_field(
            name="Rareté",
            value=data.get("rarity", "—").capitalize(),
            inline=True
        )

        if "image_uris" in data:
            embed.set_image(url=data["image_uris"].get("normal"))

        embed.set_footer(
            text=f"Illustration : {data.get('artist', 'Inconnu')} • Source : Scryfall"
        )

        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtgcarte",
        description="Affiche une carte Magic: The Gathering"
    )
    @app_commands.describe(
        nom="Nom de la carte",
        lang="Langue souhaitée (en, fr, de, es, it, pt, jp, kr, zhs, zht, ...)"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mtgcarte(
        self,
        interaction: discord.Interaction,
        nom: str,
        lang: str = "en"
    ):
        await interaction.response.defer()
        data = await self.fetch_card(nom, lang)
        if not data:
            return await safe_respond(interaction, "❌ Carte introuvable.")
        embed = self.build_card_embed(data)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mtgcarte")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mtgcarte(
        self,
        ctx: commands.Context,
        nom: str,
        lang: str = "en"
    ):
        data = await self.fetch_card(nom, lang)
        if not data:
            return await safe_send(ctx.channel, "❌ Carte introuvable.")
        embed = self.build_card_embed(data)
        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MTGCarte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "MagicTCG"
    await bot.add_cog(cog)
