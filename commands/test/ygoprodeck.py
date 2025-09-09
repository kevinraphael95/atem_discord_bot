# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygoprodeck.py — Commande interactive /ygoprodeck et !ygoprodeck
# Objectif : Rechercher une carte dans la base YGOPRODECK et afficher ses infos
# Catégorie : Test
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from utils.discord_utils import safe_send, safe_respond  

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ API et cache
# ────────────────────────────────────────────────────────────────────────────────
YGOPRODECK_API = "https://ygoprodeck.com/api/autocomplete.php"
SUGGESTION_CACHE = {}

async def search_card(term: str):
    """Recherche une carte via l'API YGOPRODECK."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(YGOPRODECK_API, params={"query": term}, headers={"Accept": "application/json"}) as resp:
                if resp.status != 200:
                    return {"error": f"HTTP {resp.status}"}
                return await resp.json()
    except Exception as e:
        print(f"[ERREUR API] {e}")
        return {"error": str(e)}

def ygoprodeck_card_url(name: str):
    """Génère l'URL publique YGOPRODECK pour la carte."""
    from urllib.parse import quote
    return f"https://ygoprodeck.com/card-database/?name={quote(name)}"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class YGOPRODECKCommand(commands.Cog):
    """
    Commande /ygoprodeck et !ygoprodeck — Recherche une carte YGOPRODECK
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Autocomplete
    # ────────────────────────────────────────────────────────────────────────────
    async def autocomplete_term(self, interaction: discord.Interaction, current: str):
        try:
            response = await search_card(current)
            if "suggestions" in response:
                options = []
                for sug in response["suggestions"][:25]:
                    SUGGESTION_CACHE[sug["name"]] = sug["data"]
                    options.append(app_commands.Choice(name=sug["name"], value=sug["name"]))
                return options
            return []
        except Exception as e:
            print(f"[ERREUR Autocomplete] {e}")
            return []

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygoprodeck",
        description="Rechercher une carte dans la base YGOPRODECK."
    )
    @app_commands.describe(
        term="Nom anglais de la carte à rechercher"
    )
    @app_commands.autocomplete(term=autocomplete_term)
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_ygoprodeck(self, interaction: discord.Interaction, term: str):
        try:
            await interaction.response.defer()
            content = None
            if term in SUGGESTION_CACHE:
                content = f"Carte trouvée : ID {SUGGESTION_CACHE[term]}"
            else:
                response = await search_card(term)
                if "suggestions" in response and response["suggestions"]:
                    content = f"Carte trouvée : ID {response['suggestions'][0]['data']}"
                    SUGGESTION_CACHE[response['suggestions'][0]['name']] = response['suggestions'][0]['data']
                else:
                    content = f"❌ Aucune carte trouvée pour `{term}`.\n{ygoprodeck_card_url(term)}"
            await interaction.followup.send(content)
        except Exception as e:
            print(f"[ERREUR /ygoprodeck] {e}")
            await safe_respond(interaction, f"❌ Une erreur est survenue pour `{term}`.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygoprodeck")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_ygoprodeck(self, ctx: commands.Context, *, term: str):
        try:
            content = None
            if term in SUGGESTION_CACHE:
                content = f"Carte trouvée : ID {SUGGESTION_CACHE[term]}"
            else:
                response = await search_card(term)
                if "suggestions" in response and response["suggestions"]:
                    content = f"Carte trouvée : ID {response['suggestions'][0]['data']}"
                    SUGGESTION_CACHE[response['suggestions'][0]['name']] = response['suggestions'][0]['data']
                else:
                    content = f"❌ Aucune carte trouvée pour `{term}`.\n{ygoprodeck_card_url(term)}"
            await safe_send(ctx.channel, content)
        except Exception as e:
            print(f"[ERREUR !ygoprodeck] {e}")
            await safe_send(ctx.channel, f"❌ Une erreur est survenue pour `{term}`.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOPRODECKCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
