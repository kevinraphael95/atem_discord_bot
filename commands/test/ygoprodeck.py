# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygoprodeck.py — Commande interactive /ygoprodeck et !ygoprodeck
# Objectif : Rechercher une carte dans la base YGOPRODECK
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
from discord.ui import View
from datetime import datetime

from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.ygoprodeck_utils import search_card, ygoprodeck_card

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class YGOPRODECKCommand(commands.Cog):
    """
    Commande /ygoprodeck et !ygoprodeck — Rechercher une carte dans YGOPRODECK
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.suggestion_cache = {}  # {name: card_id}

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _search_card(self, interaction_or_ctx, term: str):
        start_time = datetime.utcnow()
        try:
            # Vérifier le cache
            if term in self.suggestion_cache:
                card_id = self.suggestion_cache[term]
                content = ygoprodeck_card(card_id)
            else:
                response = await search_card(term)
                if "suggestions" in response and response["suggestions"]:
                    first = response["suggestions"][0]
                    self.suggestion_cache[first["name"]] = first["data"]
                    content = ygoprodeck_card(first["data"])
                else:
                    search_url = f"<https://ygoprodeck.com/card-database/?name={term}>"
                    content = f"{response.get('error', 'Carte introuvable')}\n{search_url}"

            await safe_edit(interaction_or_ctx, content)
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            return latency

        except Exception as e:
            await safe_edit(interaction_or_ctx, f"❌ Une erreur est survenue : {e}")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygoprodeck",
        description="Rechercher une carte dans la base YGOPRODECK"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_ygoprodeck(self, interaction: discord.Interaction, term: str):
        """Commande slash principale."""
        await interaction.response.defer()
        await self._search_card(interaction, term)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygoprodeck")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_ygoprodeck(self, ctx: commands.Context, *, term: str):
        """Commande préfixe principale."""
        await self._search_card(ctx, term)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOPRODECKCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
