# ────────────────────────────────────────────────────────────────────────────────
# 📌 mtgcarte.py — Commande /mtgcarte et !mtgcarte
# Objectif : Afficher une carte Magic: The Gathering via Scryfall
#           Peut afficher une carte aléatoire si aucun nom n’est fourni
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

from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Constantes Scryfall
# ────────────────────────────────────────────────────────────────────────────────
SCRYFALL_API = "https://api.scryfall.com"

HEADERS = {
    "User-Agent": "VaactMagicBot/1.0",
    "Accept": "application/json"
}

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
    async def fetch_card(self, name: str | None = None) -> dict | None:
        """
        Récupère une carte Magic depuis Scryfall en réutilisant la session aiohttp du bot.
        Si name=None, renvoie une carte aléatoire.
        """
        session = self.bot.aiohttp_session  # ✅ Session globale du bot

        if name:
            url = f"{SCRYFALL_API}/cards/named"
            params = {"fuzzy": name}
        else:
            url = f"{SCRYFALL_API}/cards/random"
            params = {}

        async with session.get(url, params=params, headers=HEADERS) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Création de l'embed carte
    # ────────────────────────────────────────────────────────────────────────────
    def build_card_embed(self, data: dict) -> discord.Embed:
        embed = discord.Embed(
            title=data.get("name", "Carte inconnue"),
            description=data.get("oracle_text", "—"),
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Mana",
            value=data.get("mana_cost", "—"),
            inline=True
        )
        embed.add_field(
            name="Type",
            value=data.get("type_line", "—"),
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
            embed.set_image(url=data["image_uris"]["normal"])

        embed.set_footer(
            text=f"Illustration : {data.get('artist', 'Inconnu')} • Source : Scryfall"
        )

        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtgcarte",
        description="Affiche une carte Magic: The Gathering (aléatoire si aucun nom)"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mtgcarte(
        self,
        interaction: discord.Interaction,
        nom: str | None = None
    ):
        await interaction.response.defer()
        data = await self.fetch_card(nom)
        if not data:
            await safe_respond(interaction, "❌ Carte introuvable.")
            return
        embed = self.build_card_embed(data)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mtgcarte", help="Affiche une carte Magic: The Gathering (aléatoire si aucun nom)")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mtgcarte(self, ctx: commands.Context, *, nom: str | None = None):
        data = await self.fetch_card(nom)
        if not data:
            await safe_send(ctx.channel, "❌ Carte introuvable.")
            return
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
