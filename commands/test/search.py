# ────────────────────────────────────────────────────────────────────────────────
# 📌 search.py — Commande interactive !search
# Objectif : Trouver toutes les informations d'une carte Yu-Gi-Oh!
# Catégorie : Yu-Gi-Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
from utils.discord_utils import safe_send, safe_edit, safe_respond  # ✅ conformes au template

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Fonctions utilitaires
# ────────────────────────────────────────────────────────────────────────────────
async def get_card_by_name(name: str):
    """Recherche une carte via l'API YGOPRODECK par son nom."""
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={name}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data["data"][0] if "data" in data else None


def build_card_embed(card: dict) -> discord.Embed:
    """Construit un embed Discord avec les infos d'une carte Yu-Gi-Oh!"""
    embed = discord.Embed(
        title=card.get("name", "Carte inconnue"),
        description=card.get("desc", "Pas de description."),
        color=discord.Color.blue()
    )

    # Image de la carte
    if "card_images" in card:
        embed.set_image(url=card["card_images"][0]["image_url"])

    # Infos principales
    atk, defense, level = card.get("atk"), card.get("def"), card.get("level")
    stats = []
    if atk is not None: stats.append(f"ATK {atk}")
    if defense is not None: stats.append(f"DEF {defense}")
    if level is not None: stats.append(f"Niveau {level}")
    if stats:
        embed.add_field(name="Statistiques", value=" | ".join(stats), inline=False)

    # Type & Race
    if "type" in card:
        embed.add_field(name="Type", value=card["type"], inline=True)
    if "race" in card:
        embed.add_field(name="Race", value=card["race"], inline=True)

    # Archétype si dispo
    if "archetype" in card:
        embed.add_field(name="Archétype", value=card["archetype"], inline=True)

    return embed


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class SearchCommand(commands.Cog):
    """
    Commande !search — Recherche une carte Yu-Gi-Oh! par son nom
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="search",
        help="Cherche une carte Yu-Gi-Oh! par son nom.",
        description="Exemple: !search Magicien Sombre"
    )
    async def search(self, ctx: commands.Context, *, name: str):
        """Commande principale avec affichage d'une carte Yu-Gi-Oh!"""
        try:
            card = await get_card_by_name(name)
            if not card:
                await safe_send(ctx.channel, f"❌ Impossible de trouver une carte pour `{name}`.")
                return

            embed = build_card_embed(card)
            await safe_send(ctx.channel, embed=embed)

        except Exception as e:
            print(f"[ERREUR !search] {e}")
            await safe_send(ctx.channel, "❌ Une erreur inattendue est survenue.")


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = SearchCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Yu-Gi-Oh"
    await bot.add_cog(cog)
