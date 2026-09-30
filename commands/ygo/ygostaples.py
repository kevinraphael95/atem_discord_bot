# ================================================================================
# 📌 staples.py — Commande interactive /staples et !staples
# Objectif :
#   - Récupère les cartes Staples depuis l'API YGOPRODeck
#   - Affiche les résultats avec pagination (20 cartes/page)
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Version optimisée : session partagée + cache 1h
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import json
import time
from pathlib import Path
from utils.discord_utils import safe_send, safe_respond

# ================================================================================
# 📖 Chargement du dictionnaire de traduction des types
# ================================================================================
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
TYPE_EMOJI       = CARDINFO.get("TYPE_EMOJI", {})
ATTRIBUT_EMOJI   = CARDINFO.get("ATTRIBUT_EMOJI", {})

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

# ================================================================================
# 🎛️ View — Pagination des staples
# ================================================================================
class StaplesPagination(discord.ui.View):
    def __init__(self, staples: list[dict], per_page: int = 20):
        super().__init__(timeout=180)
        self.staples = staples
        self.per_page = per_page
        self.page = 0

    def get_page_data(self):
        start = self.page * self.per_page
        end = start + self.per_page
        return self.staples[start:end]

    async def update_embed(self, interaction: discord.Interaction):
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

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Staples(commands.Cog):
    """Commande /ygostaples et !ygostaples — Liste des cartes Staples"""

    API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes&language=fr"
    CACHE_TTL = 3600  # 1 heure

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cache = None
        self._cache_time = 0

    async def fetch_staples(self):
        """Récupère les staples avec cache 1h."""
        now = time.monotonic()
        if self._cache and (now - self._cache_time) < self.CACHE_TTL:
            return self._cache

        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return None

        try:
            async with session.get(self.API_URL) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                self._cache = data.get("data", [])
                self._cache_time = now
                return self._cache
        except Exception as e:
            print(f"[staples] Erreur : {e}")
            return None

    def _build_embed(self, staples, view):
        """Construit l'embed de la première page."""
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
        return embed

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ygostaples",
        description="Affiche une liste de cartes considérées comme staples (20 par page)."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_staples(self, interaction: discord.Interaction):
        await interaction.response.defer()
        staples = await self.fetch_staples()
        if not staples:
            return await safe_respond(interaction, "❌ Impossible de récupérer les cartes staples.")

        view = StaplesPagination(staples)
        embed = self._build_embed(staples, view)
        await interaction.edit_original_response(embed=embed, view=view)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="ygostaples")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_staples(self, ctx: commands.Context):
        staples = await self.fetch_staples()
        if not staples:
            return await safe_send(ctx.channel, "❌ Impossible de récupérer les cartes staples.")

        view = StaplesPagination(staples)
        embed = self._build_embed(staples, view)
        await safe_send(ctx.channel, embed=embed, view=view)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Staples(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
