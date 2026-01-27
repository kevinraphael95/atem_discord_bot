# ────────────────────────────────────────────────────────────────────────────────
# 📌 lorcarte.py — Commande /lorcarte et !lorcarte
# Objectif : Affiche une carte Disney Lorcana via Lorcana-api.com
#           Peut afficher une carte aléatoire si aucun nom n’est fourni
# Catégorie : LorcanaTCG
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
import random
import urllib.parse

from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Constantes Lorcana
# ────────────────────────────────────────────────────────────────────────────────
LORCANA_API_FETCH = "https://api.lorcana-api.com/cards/fetch"
LORCANA_API_ALL = "https://api.lorcana-api.com/cards/all"

HEADERS = {
    "User-Agent": "VaactLorcanaBot/1.0",
    "Accept": "application/json"
}

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Lorcarte(commands.Cog):
    """
    Commande /lorcarte et !lorcarte — Affiche une carte Lorcana
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Utilitaire API
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_card(self, name: str | None = None) -> dict | None:
        """Récupère une carte Lorcana par nom (fuzzy) ou aléatoire si name=None."""
        session = self.bot.aiohttp_session

        if name:
            # Recherche fuzzy
            params = {"search": f"Name~{name}", "pagesize": 1, "page": 1}
            url = f"{LORCANA_API_FETCH}?{urllib.parse.urlencode(params)}"
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data:
                    return data[0]

        # Fallback aléatoire
        # On récupère 1000 cartes max et on choisit une aléatoire
        params = {"pagesize": 1000, "page": 1}
        url = f"{LORCANA_API_ALL}?{urllib.parse.urlencode(params)}"
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return random.choice(data) if data else None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Création de l'embed carte
    # ────────────────────────────────────────────────────────────────────────────
    def build_card_embed(self, data: dict) -> discord.Embed:
        name = data.get("Name", "Carte inconnue")
        type_ = data.get("Type", "—")
        cost = data.get("Cost", "—")
        color = data.get("Color", "—")
        rarity = data.get("Rarity", "—")
        set_name = data.get("Set_Name", "—")
        image = data.get("Image")
        body = data.get("Body_Text", "Pas de description disponible.")
        flavor = data.get("Flavor_Text")

        embed = discord.Embed(
            title=name,
            description=body,
            color=discord.Color.purple()
        )

        embed.add_field(name="Type", value=type_, inline=True)
        embed.add_field(name="Coût", value=cost, inline=True)
        embed.add_field(name="Couleur", value=color, inline=True)
        embed.add_field(name="Rareté", value=rarity, inline=True)
        embed.add_field(name="Set", value=set_name, inline=True)
        if flavor:
            embed.add_field(name="Lore", value=flavor, inline=False)

        if image:
            embed.set_image(url=image)

        embed.set_footer(text="💭 Source : Lorcana-api.com")
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="lorcarte",
        description="Affiche une carte Disney Lorcana (aléatoire si aucun nom)"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_lorcarte(
        self,
        interaction: discord.Interaction,
        nom: str | None = None
    ):
        await interaction.response.defer()
        card = await self.fetch_card(nom)
        if not card:
            await safe_respond(interaction, f"❌ Carte '{nom}' introuvable.")
            return
        embed = self.build_card_embed(card)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="lorcarte", help="Affiche une carte Disney Lorcana (aléatoire si aucun nom)")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_lorcarte(self, ctx: commands.Context, *, nom: str | None = None):
        card = await self.fetch_card(nom)
        if not card:
            await safe_send(ctx.channel, f"❌ Carte '{nom}' introuvable.")
            return
        embed = self.build_card_embed(card)
        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Lorcarte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "LorcanaTCG"
    await bot.add_cog(cog)
