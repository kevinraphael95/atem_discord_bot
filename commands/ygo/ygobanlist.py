# ================================================================================
# 📌 banlist.py — Commande interactive /banlist et !banlist
# Objectif :
#   - Affiche les cartes d'une banlist (TCG, OCG, GOAT)
#   - Regroupées par statut (Interdite / Limitée / Semi-limitée)
#   - Pagination interactive (20 cartes par page) via boutons
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import json
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

# ================================================================================
# 🏷️ Statuts de banlist : ordre d'affichage, libellés FR, emoji
# ================================================================================
STATUS_ORDER = ["Banned", "Limited", "Semi-Limited"]
STATUS_LABELS = {
    "Banned": ("🚫", "Interdites"),
    "Limited": ("⚠️", "Limitées"),
    "Semi-Limited": ("⚡", "Semi-limitées"),
}

def group_by_status(cards: list[dict], ban_key: str) -> dict[str, list[dict]]:
    """Regroupe les cartes par statut de banlist (Interdite/Limitée/Semi-limitée)."""
    groups = {status: [] for status in STATUS_ORDER}
    for c in cards:
        status = c.get("banlist_info", {}).get(ban_key)
        if status in groups:
            groups[status].append(c)
    return groups

def flatten_grouped(groups: dict[str, list[dict]]) -> list[tuple[str, dict]]:
    """Aplati les groupes en liste (statut, carte) triée par statut puis par nom, pour la pagination."""
    flat = []
    for status in STATUS_ORDER:
        for c in sorted(groups[status], key=lambda c: c.get("name", "")):
            flat.append((status, c))
    return flat

# ================================================================================
# 🎛️ View — Pagination des banlists
# ================================================================================
class BanlistPagination(discord.ui.View):
    def __init__(self, banlist_type: str, groups: dict[str, list[dict]], per_page: int = 20):
        super().__init__(timeout=180)
        self.banlist_type = banlist_type
        self.groups = groups
        self.flat = flatten_grouped(groups)
        self.per_page = per_page
        self.page = 0
        self.message = None

    def _total_pages(self) -> int:
        return max(1, (len(self.flat) - 1) // self.per_page + 1)

    def build_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        current = self.flat[start:end]

        # Résumé des totaux par statut (toujours affiché, quelle que soit la page)
        summary = " • ".join(
            f"{emoji} {label} : {len(self.groups[status])}"
            for status, (emoji, label) in STATUS_LABELS.items()
        )

        lines = []
        last_status = None
        for status, card in current:
            if status != last_status:
                emoji, label = STATUS_LABELS[status]
                lines.append(f"\n**{emoji} {label}**")
                last_status = status
            lines.append(f"• **{card['name']}** — {translate_card_type(card.get('type', 'Inconnu'))}")

        description = summary + "\n" + "\n".join(lines) if lines else summary + "\nAucune carte à afficher."

        embed = discord.Embed(
            title=f"📌 Banlist {self.banlist_type.upper()} (Page {self.page + 1}/{self._total_pages()})",
            description=description,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"{len(self.flat)} cartes au total • 20 par page")
        return embed

    async def update_embed(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % self._total_pages()
        await self.update_embed(interaction)

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % self._total_pages()
        await self.update_embed(interaction)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_send(self.message, view=self)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Banlist(commands.Cog):
    """Commande /banlist et !banlist — Affiche les cartes d'une banlist (TCG, OCG, GOAT)"""

    BASE_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
    BAN_KEY = {"tcg": "ban_tcg", "ocg": "ban_ocg", "goat": "ban_goat"}

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_banlist(self, banlist_type: str):
        """Récupère les cartes selon la banlist choisie (noms en français), regroupées par statut."""
        params = {"banlist": banlist_type, "sort": "name", "language": "fr"}
        async with self.bot.aiohttp_session.get(self.BASE_URL, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            cards = data.get("data", [])
            if not cards:
                return None
            return group_by_status(cards, self.BAN_KEY[banlist_type])

    async def _run(self, banlist_type: str):
        """Logique commune slash/prefix : retourne (groups, error_message)."""
        banlist_type = banlist_type.lower()
        if banlist_type not in self.BAN_KEY:
            return None, "❌ Type de banlist invalide. Utilise `tcg`, `ocg` ou `goat`."
        groups = await self.fetch_banlist(banlist_type)
        if groups is None:
            return None, "❌ Impossible de récupérer les cartes."
        return groups, None

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ygobanlist",
        description="Affiche les cartes d'une banlist (tcg, ocg ou goat) avec pagination."
    )
    @app_commands.describe(banlist="Type de banlist: tcg, ocg, goat")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_banlist(self, interaction: discord.Interaction, banlist: str = "tcg"):
        await interaction.response.defer()
        groups, error = await self._run(banlist)
        if error:
            return await safe_respond(interaction, error)

        view = BanlistPagination(banlist.lower(), groups)
        embed = view.build_embed()
        await interaction.followup.send(embed=embed, view=view)
        view.message = await interaction.original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="ygobanlist", aliases=["ygobl", "ybanlist", "ybl"], help="Affiche les cartes d'une banlist (tcg, ocg ou goat) avec pagination.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_banlist(self, ctx: commands.Context, banlist: str = "tcg"):
        groups, error = await self._run(banlist)
        if error:
            return await safe_send(ctx.channel, error)

        view = BanlistPagination(banlist.lower(), groups)
        embed = view.build_embed()
        view.message = await safe_send(ctx.channel, embed=embed, view=view)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Banlist(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
