# ────────────────────────────────────────────────────────────────────────────────
# 📌 magic_tcg.py — Commandes Magic The Gathering (Scryfall)
# Catégorie : MagicTCG
# Commandes :
#   /mtgcarte        → Affiche une carte
#   /mtgrandom       → Carte aléatoire
#   /mtgset          → Infos sur un set
#   /mtglatestset    → Dernier set sorti
#   /mtgart          → Art d'une carte
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

from utils.discord_utils import safe_respond, safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Constantes Scryfall
# ────────────────────────────────────────────────────────────────────────────────
SCRYFALL = "https://api.scryfall.com"

HEADERS = {
    "User-Agent": "VaactMagicBot/1.0",
    "Accept": "application/json"
}

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MagicTCG(commands.Cog):
    """
    Commandes Magic The Gathering basées sur l'API Scryfall
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔍 /mtgcarte
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtgcarte",
        description="Affiche une carte Magic"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def mtg_carte(self, interaction: discord.Interaction, nom: str):
        data = await self.fetch_card({"fuzzy": nom})
        if not data:
            return await safe_respond(interaction, "❌ Carte introuvable.")

        embed = self.card_embed(data)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🎲 /mtgrandom
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtgrandom",
        description="Affiche une carte Magic aléatoire"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def mtg_random(self, interaction: discord.Interaction):
        data = await self.fetch_endpoint("/cards/random")
        embed = self.card_embed(data)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 📦 /mtgset
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtgset",
        description="Affiche les informations d'un set Magic"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def mtg_set(self, interaction: discord.Interaction, set_code: str):
        data = await self.fetch_endpoint(f"/sets/{set_code.lower()}")
        if not data:
            return await safe_respond(interaction, "❌ Set introuvable.")

        embed = discord.Embed(
            title=data["name"],
            description=f"Code : `{data['code'].upper()}`",
            color=discord.Color.gold()
        )

        embed.add_field(name="Type", value=data["set_type"], inline=True)
        embed.add_field(name="Cartes", value=data["card_count"], inline=True)
        embed.add_field(name="Sortie", value=data["released_at"], inline=True)

        embed.set_footer(text="Source : Scryfall")

        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🆕 /mtglatestset
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtglatestset",
        description="Affiche le dernier set Magic sorti"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def mtg_latest_set(self, interaction: discord.Interaction):
        data = await self.fetch_endpoint("/sets")
        latest = next(s for s in data["data"] if s["released_at"])

        embed = discord.Embed(
            title=latest["name"],
            description=f"Code : `{latest['code'].upper()}`",
            color=discord.Color.green()
        )

        embed.add_field(name="Sortie", value=latest["released_at"], inline=True)
        embed.add_field(name="Cartes", value=latest["card_count"], inline=True)

        embed.set_footer(text="Source : Scryfall")

        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🎨 /mtgart
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtgart",
        description="Affiche l'art d'une carte Magic"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def mtg_art(self, interaction: discord.Interaction, nom: str):
        data = await self.fetch_card({"fuzzy": nom})
        if not data or "image_uris" not in data:
            return await safe_respond(interaction, "❌ Art indisponible.")

        embed = discord.Embed(
            title=data["name"],
            color=discord.Color.dark_teal()
        )

        embed.set_image(url=data["image_uris"]["art_crop"])
        embed.set_footer(
            text=f"Illustration : {data['artist']} • Source : Scryfall"
        )

        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🧩 Utilitaires API
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_card(self, params: dict):
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(f"{SCRYFALL}/cards/named", params=params) as r:
                return await r.json() if r.status == 200 else None

    async def fetch_endpoint(self, endpoint: str):
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(f"{SCRYFALL}{endpoint}") as r:
                return await r.json() if r.status == 200 else None

    def card_embed(self, data: dict) -> discord.Embed:
        embed = discord.Embed(
            title=data["name"],
            description=data.get("oracle_text", "—"),
            color=discord.Color.purple()
        )

        embed.add_field(name="Mana", value=data.get("mana_cost", "—"), inline=True)
        embed.add_field(name="Type", value=data["type_line"], inline=False)
        embed.add_field(name="Set", value=data["set_name"], inline=True)
        embed.add_field(name="Rareté", value=data["rarity"].capitalize(), inline=True)

        if "image_uris" in data:
            embed.set_image(url=data["image_uris"]["normal"])

        embed.set_footer(
            text=f"Illustration : {data['artist']} • Source : Scryfall"
        )

        return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MagicTCG(bot)
    for command in cog.get_commands():
        command.category = "MagicTCG"
    await bot.add_cog(cog)
