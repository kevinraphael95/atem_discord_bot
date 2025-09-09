# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygoprodeck.py — Commande interactive /ygoprodeck et !ygoprodeck
# Objectif : Rechercher une carte dans la base YGOPRODECK et afficher ses infos complètes
# Catégorie : Test
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import aiohttp

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ API — Constantes et utilitaires
# ────────────────────────────────────────────────────────────────────────────────
API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
SUPPORTED_LANGS = ["en", "fr", "de", "it", "pt"]

async def fetch_card(term: str, lang: str = "fr"):
    """Recherche une carte via YGOPRODECK API."""
    if lang not in SUPPORTED_LANGS:
        lang = "fr"
    params = {"name": term, "language": lang}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data["data"][0] if "data" in data and len(data["data"]) > 0 else None
    except Exception as e:
        print(f"[ERREUR API] {e}")
        return None

def build_card_embed(card: dict, lang: str) -> discord.Embed:
    """Construit un embed riche pour afficher une carte."""
    name = card.get("name", "Carte inconnue")
    desc = card.get("desc", "Aucune description disponible.")
    card_type = card.get("type", "Inconnu")
    atk = card.get("atk", "?")
    defense = card.get("def", "?")
    level = card.get("level", "?")
    race = card.get("race", "Inconnu")
    attribute = card.get("attribute", "Inconnu")

    embed = discord.Embed(
        title=f"{name} ({lang.upper()})",
        description=desc[:1024],
        color=discord.Color.dark_blue()
    )
    embed.add_field(name="Type", value=card_type, inline=True)
    if "Monster" in card_type:
        embed.add_field(name="ATK", value=str(atk), inline=True)
        embed.add_field(name="DEF", value=str(defense), inline=True)
        embed.add_field(name="Niveau", value=str(level), inline=True)
        embed.add_field(name="Race", value=race, inline=True)
        embed.add_field(name="Attribut", value=attribute, inline=True)

    if "card_images" in card and card["card_images"]:
        embed.set_image(url=card["card_images"][0]["image_url"])
    embed.set_footer(text=f"ID: {card.get('id', '???')}")

    embed.add_field(
        name="Lien YGOPRODECK",
        value=f"[Voir la carte](https://ygoprodeck.com/card/?search={name.replace(' ', '+')})",
        inline=False
    )

    return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class YGOPRODECKCommand(commands.Cog):
    """
    Commande /ygoprodeck et !ygoprodeck — Rechercher une carte dans YGOPRODECK
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cache = {}  # {(term, lang): card}

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _search_card(self, interaction_or_ctx, term: str, lang: str = "fr"):
        start_time = datetime.utcnow()
        try:
            cache_key = (term.lower(), lang)
            if cache_key in self.cache:
                card = self.cache[cache_key]
            else:
                card = await fetch_card(term, lang)
                if card:
                    self.cache[cache_key] = card

            if not card:
                msg = f"❌ Impossible de trouver une carte pour `{term}` en **{lang.upper()}**."
                if isinstance(interaction_or_ctx, discord.Interaction):
                    await safe_edit(interaction_or_ctx, msg)
                else:
                    await safe_send(interaction_or_ctx, msg)
                return

            embed = build_card_embed(card, lang)
            if isinstance(interaction_or_ctx, discord.Interaction):
                await safe_edit(interaction_or_ctx, embed=embed)
            else:
                await safe_send(interaction_or_ctx, embed=embed)

            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            return latency

        except Exception as e:
            msg = f"❌ Une erreur est survenue : {e}"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await safe_edit(interaction_or_ctx, msg)
            else:
                await safe_send(interaction_or_ctx, msg)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygoprodeck",
        description="Rechercher une carte dans la base YGOPRODECK"
    )
    @app_commands.describe(
        term="Nom de la carte à rechercher",
        lang="Langue (fr, en, de, it, pt)"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_ygoprodeck(self, interaction: discord.Interaction, term: str, lang: str = "fr"):
        """Commande slash principale."""
        await interaction.response.defer()
        await self._search_card(interaction, term, lang)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygoprodeck")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_ygoprodeck(self, ctx: commands.Context, lang: str, *, term: str):
        """
        !ygoprodeck <lang> <nom_de_carte>
        Exemple: !ygoprodeck fr Dragon Blanc aux Yeux Bleus
        """
        await self._search_card(ctx, term, lang)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOPRODECKCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
