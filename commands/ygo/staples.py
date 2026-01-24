# ────────────────────────────────────────────────────────────────────────────────
# 📌 staples.py — Commande interactive /staples et !staples
# Objectif :
#   - Récupère les cartes Staples depuis l’API YGOPRODeck
#   - Affiche les résultats avec pagination (20 cartes/page)
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
from pathlib import Path
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 📖 Chargement du dictionnaire de traduction des types
# ────────────────────────────────────────────────────────────────────────────────
CARDINFO_PATH = Path("data/cardinfofr.json")
try:
    with CARDINFO_PATH.open("r", encoding="utf-8") as f:
        CARDINFO = json.load(f)
except FileNotFoundError:
    print("[ERREUR] Fichier data/cardinfofr.json introuvable.")
    CARDINFO = {
        "TYPE_TRANSLATION": {},
        "TYPE_EMOJI": {},
        "ATTRIBUT_EMOJI": {}
    }

TYPE_TRANSLATION = CARDINFO.get("TYPE_TRANSLATION", {})
TYPE_EMOJI = CARDINFO.get("TYPE_EMOJI", {})
ATTRIBUT_EMOJI = CARDINFO.get("ATTRIBUT_EMOJI", {})

def translate_card_type(type_str: str) -> str:
    """Traduit le type de carte anglais → français avec emoji si disponible."""
    if not type_str:
        return "Inconnu"
    t = type_str.lower()
    for eng, fr in TYPE_TRANSLATION.items():
        if eng in t:
            emoji = TYPE_EMOJI.get(eng, "")
            return f"{emoji} {fr}" if emoji else fr
    return type_str

def translate_card_attribute(attr_str: str) -> str:
    """Traduit l'attribut de la carte avec emoji."""
    if not attr_str:
        return "Inconnu"
    return ATTRIBUT_EMOJI.get(attr_str.upper(), attr_str)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination des staples
# ────────────────────────────────────────────────────────────────────────────────
class StaplesPagination(discord.ui.View):
    def __init__(self, staples: list[dict], per_page: int = 20):
        super().__init__(timeout=180)
        self.staples = staples
        self.per_page = per_page
        self.page = 0

    def get_page_data(self):
        """Retourne les cartes pour la page actuelle."""
        start = self.page * self.per_page
        end = start + self.per_page
        return self.staples[start:end]

    async def update_embed(self, interaction: discord.Interaction):
        """Met à jour l'embed affiché avec noms, types et attributs en français."""
        current = self.get_page_data()
        total_pages = (len(self.staples) - 1) // self.per_page + 1

        description = "\n".join(
            f"**{c['name']}** — {translate_card_type(c.get('type', 'Inconnu'))} — {translate_card_attribute(c.get('attribute', 'Inconnu'))}"
            for c in current
        )

        embed = discord.Embed(
            title=f"📌 Cartes Staples (Page {self.page + 1}/{total_pages})",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{len(self.staples)} cartes au total • {self.per_page} par page")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % ((len(self.staples) - 1) // self.per_page + 1)
        await self.update_embed(interaction)

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % ((len(self.staples) - 1) // self.per_page + 1)
        await self.update_embed(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Staples(commands.Cog):
    """Commande /staples et !staples — Liste des cartes Staples"""

    API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes&language=fr"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_staples(self):
        """Récupère les cartes staples depuis l'API (noms, types et attributs en français)."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("data", [])

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="staples",
        description="Affiche une liste de cartes considérées comme staples (20 par page)."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_staples(self, interaction: discord.Interaction):
        await safe_respond(interaction, "🔄 Récupération des cartes staples…")
        staples = await self.fetch_staples()
        if not staples:
            return await safe_respond(interaction, "❌ Impossible de récupérer les cartes staples.")

        view = StaplesPagination(staples)
        current = view.get_page_data()
        total_pages = (len(staples) - 1) // view.per_page + 1

        description = "\n".join(
            f"**{c['name']}** — {translate_card_type(c.get('type', 'Inconnu'))} — {translate_card_attribute(c.get('attribute', 'Inconnu'))}"
            for c in current
        )

        embed = discord.Embed(
            title=f"📌 Cartes Staples (Page 1/{total_pages})",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{len(staples)} cartes au total • {view.per_page} par page")
        await interaction.edit_original_response(embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="staples")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_staples(self, ctx: commands.Context):
        msg = await safe_send(ctx.channel, "🔄 Récupération des cartes staples…")
        staples = await self.fetch_staples()
        if not staples:
            return await safe_send(ctx.channel, "❌ Impossible de récupérer les cartes staples.")

        view = StaplesPagination(staples)
        current = view.get_page_data()
        total_pages = (len(staples) - 1) // view.per_page + 1

        description = "\n".join(
            f"**{c['name']}** — {translate_card_type(c.get('type', 'Inconnu'))} — {translate_card_attribute(c.get('attribute', 'Inconnu'))}"
            for c in current
        )

        embed = discord.Embed(
            title=f"📌 Cartes Staples (Page 1/{total_pages})",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{len(staples)} cartes au total • {view.per_page} par page")
        await msg.edit(content=None, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Staples(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
