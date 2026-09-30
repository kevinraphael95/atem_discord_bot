# ================================================================================
# 📌 vaact_randeck.py
# Objectif : Tirer un deck custom aléatoire avec boutons interactifs
# Catégorie : VAACT
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes par utilisateur
# Version optimisée : safe_defer + fix setup
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import random

from utils.discord_utils import safe_send, safe_defer

# ================================================================================
# 📂 Chargement des données JSON
# ================================================================================
DATA_JSON_PATH = os.path.join("data", "deck_data.json")

def load_data():
    """Charge le fichier JSON contenant les decks."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {DATA_JSON_PATH} : {e}")
        return {}

# ================================================================================
# 🎛️ View Boutons Deck
# ================================================================================
class DeckLinkView(View):
    def __init__(self, links: dict):
        super().__init__(timeout=120)

        for name, url in links.items():
            self.add_item(Button(label=name, url=url))

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class VaactRandeck(commands.Cog):
    """Commande /vaact_randeck et !vaact_randeck — Tire un deck custom aléatoire"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_random_deck(self, channel: discord.abc.Messageable, author: discord.Member):
        data = load_data()
        if not data:
            await safe_send(channel, "❌ Impossible de charger les données.")
            return

        decks = []

        # Construction liste exploitable
        for saison, persos in data.items():
            for duelliste, infos in persos.items():
                deck_data = infos.get("deck", {})
                if not isinstance(deck_data, dict):
                    continue

                for niveau, liens in deck_data.items():
                    if isinstance(liens, dict) and liens:
                        decks.append((saison, duelliste, niveau, liens))

        if not decks:
            await safe_send(channel, "❌ Aucun deck disponible.")
            return

        # Tirage aléatoire
        saison, duelliste, niveau, liens_dict = random.choice(decks)

        embed = discord.Embed(
            title="🎲 Deck Aléatoire Tiré !",
            color=discord.Color.random()
        )

        embed.add_field(
            name="👤 Duelliste",
            value=f"**{duelliste}** *(Saison : {saison})*",
            inline=False
        )

        embed.add_field(
            name="🎚️ Niveau",
            value=niveau,
            inline=False
        )

        embed.set_footer(
            text=f"Tiré par {author.display_name}",
            icon_url=author.display_avatar.url
        )

        view = DeckLinkView(liens_dict)

        await safe_send(channel, embed=embed, view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="vaact_randeck",
        description="Tire un deck custom aléatoire à jouer."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_vaact_randeck(self, interaction: discord.Interaction):
        # ✅ Defer sécurisé
        if not await safe_defer(interaction):
            return
        await self._send_random_deck(interaction.channel, interaction.user)
        # Pas de delete, defer = invisible

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="vaact_randeck",
        aliases=["vaactrandeck"]
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_vaact_randeck(self, ctx: commands.Context):
        await self._send_random_deck(ctx.channel, ctx.author)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = VaactRandeck(bot)   # ✅ Fix : VaactRandeck (pas Randeck)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
