# ────────────────────────────────────────────────────────────────────────────────
# 📌 banlist.py — Commande interactive /banlist et !banlist
# Objectif :
#   - Affiche les cartes d'une banlist (TCG, OCG, GOAT)
#   - Pagination interactive (20 cartes par page) via boutons
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
from pathlib import Path
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 📖 Chargement du dictionnaire de traduction des types
# ────────────────────────────────────────────────────────────────────────────────
CARDINFO_PATH = Path("data/cardinfofr.json")
try:
    with CARDINFO_PATH.open("r", encoding="utf-8") as f:
        CARDINFO = json.load(f)
except FileNotFoundError:
    print("[ERREUR] Fichier data/cardinfofr.json introuvable.")
    CARDINFO = {"TYPE_TRANSLATION": {}}

TYPE_TRANSLATION = CARDINFO.get("TYPE_TRANSLATION", {})

def translate_card_type(type_str: str) -> str:
    """Traduit le type de carte anglais → français."""
    if not type_str:
        return "Inconnu"
    t = type_str.lower()
    for eng, fr in TYPE_TRANSLATION.items():
        if eng in t:
            return fr
    return type_str

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination des banlists
# ────────────────────────────────────────────────────────────────────────────────
class BanlistPagination(discord.ui.View):
    def __init__(self, cards: list[dict], per_page: int = 20):
        super().__init__(timeout=180)
        self.cards = cards
        self.per_page = per_page
        self.page = 0

    def get_page_data(self):
        start = self.page * self.per_page
        end = start + self.per_page
        return self.cards[start:end]

    async def update_embed(self, interaction: discord.Interaction, banlist_name: str):
        current = self.get_page_data()
        total_pages = (len(self.cards) - 1) // self.per_page + 1

        description = "\n".join(
            f"**{c['name']}** — {translate_card_type(c.get('type', 'Inconnu'))}"
            for c in current
        )

        embed = discord.Embed(
            title=f"📌 Cartes sur la banlist {banlist_name.upper()} (Page {self.page + 1}/{total_pages})",
            description=description or "Aucune carte à afficher.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"{len(self.cards)} cartes au total • 20 par page")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % ((len(self.cards) - 1) // self.per_page + 1)
        await self.update_embed(interaction, self.cards[0].get("banlist_name", "TCG"))

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % ((len(self.cards) - 1) // self.per_page + 1)
        await self.update_embed(interaction, self.cards[0].get("banlist_name", "TCG"))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Banlist(commands.Cog):
    """Commande /banlist et !banlist — Affiche les cartes d'une banlist (TCG, OCG, GOAT)"""

    BASE_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_banlist(self, banlist_type: str):
        """Récupère les cartes selon la banlist choisie (noms en français)."""
        params = {"banlist": banlist_type, "sort": "name", "language": "fr"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                for c in data.get("data", []):
                    c["banlist_name"] = banlist_type
                return data.get("data", [])

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="banlist",
        description="Affiche les cartes d'une banlist (tcg, ocg ou goat) avec pagination."
    )
    @app_commands.describe(banlist="Type de banlist: tcg, ocg, goat")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_banlist(self, interaction: discord.Interaction, banlist: str = "tcg"):
        banlist_type = banlist.lower()
        if banlist_type not in ("tcg", "ocg", "goat"):
            return await safe_respond(interaction, "❌ Type de banlist invalide. Utilise `tcg`, `ocg` ou `goat`.")

        await safe_respond(interaction, f"🔄 Récupération de la banlist **{banlist_type.upper()}**…")
        cards = await self.fetch_banlist(banlist_type)
        if not cards:
            return await safe_respond(interaction, "❌ Impossible de récupérer les cartes.")

        view = BanlistPagination(cards)
        await view.update_embed(interaction, banlist_type)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="banlist", aliases=["bl"], help="Affiche les cartes d'une banlist (tcg, ocg ou goat) avec pagination.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_banlist(self, ctx: commands.Context, banlist: str = "tcg"):
        banlist_type = banlist.lower()
        if banlist_type not in ("tcg", "ocg", "goat"):
            return await safe_send(ctx.channel, "❌ Type de banlist invalide. Utilise `tcg`, `ocg` ou `goat`.")

        msg = await safe_send(ctx.channel, f"🔄 Récupération de la banlist **{banlist_type.upper()}**…")
        cards = await self.fetch_banlist(banlist_type)
        if not cards:
            return await safe_send(ctx.channel, "❌ Impossible de récupérer les cartes.")

        view = BanlistPagination(cards)
        current = view.get_page_data()
        total_pages = (len(cards) - 1) // view.per_page + 1

        description = "\n".join(
            f"**{c['name']}** — {translate_card_type(c.get('type', 'Inconnu'))}"
            for c in current
        )

        embed = discord.Embed(
            title=f"📌 Cartes sur la banlist {banlist_type.upper()} (Page 1/{total_pages})",
            description=description or "Aucune carte à afficher.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"{len(cards)} cartes au total • 20 par page")
        await msg.edit(content=None, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Banlist(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
