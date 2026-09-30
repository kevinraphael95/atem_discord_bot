# ================================================================================
# 📌 carte.py — Commande interactive !ygocarte
# Objectif :
#   - Rechercher et afficher les détails d'une carte Yu-Gi-Oh!
#   - OU tirer une carte aléatoire avec !ygocarte random
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 3 sec / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
from pathlib import Path
import sqlite3

from utils.discord_utils import safe_send, safe_defer
from utils.vaact_utils import DB_PATH, get_or_create_profile
from utils.card_utils import fetch_card_full

# ================================================================================
# 🎨 Chargement décorations et couleurs (avec reload à chaud possible)
# ================================================================================
CARDINFO_PATH = Path("data/cardinfofr.json")

CARDINFO = {}
ATTRIBUT_EMOJI         = {}
TYPE_EMOJI             = {}
TYPE_TRANSLATION       = {}
SPELL_RACE_TRANSLATION = {}
TRAP_RACE_TRANSLATION  = {}
FRAME_TYPE_TRANSLATION = {}
BANLIST_TRANSLATION    = {}
TYPE_COLOR             = {}


def load_cardinfo():
    """Charge (ou recharge) data/cardinfofr.json et reconstruit les dicts globaux."""
    global CARDINFO, ATTRIBUT_EMOJI, TYPE_EMOJI, TYPE_TRANSLATION
    global SPELL_RACE_TRANSLATION, TRAP_RACE_TRANSLATION
    global FRAME_TYPE_TRANSLATION, BANLIST_TRANSLATION, TYPE_COLOR

    try:
        with CARDINFO_PATH.open("r", encoding="utf-8") as f:
            CARDINFO = json.load(f)
    except FileNotFoundError:
        print("[ERREUR] Fichier data/cardinfofr.json introuvable.")
        CARDINFO = {}
    except json.JSONDecodeError as e:
        print(f"[ERREUR] cardinfofr.json mal formé : {e}")
        CARDINFO = {}

    ATTRIBUT_EMOJI         = CARDINFO.get("ATTRIBUT_EMOJI", {})
    TYPE_EMOJI             = CARDINFO.get("TYPE_EMOJI", {})
    TYPE_TRANSLATION       = CARDINFO.get("TYPE_TRANSLATION", {})
    SPELL_RACE_TRANSLATION = CARDINFO.get("SPELL_RACE_TRANSLATION", {})
    TRAP_RACE_TRANSLATION  = CARDINFO.get("TRAP_RACE_TRANSLATION", {})
    FRAME_TYPE_TRANSLATION = CARDINFO.get("FRAME_TYPE_TRANSLATION", {})
    BANLIST_TRANSLATION    = CARDINFO.get("BANLIST_TRANSLATION", {})

    TYPE_COLOR = {}
    for key, hex_code in CARDINFO.get("TYPE_COLOR", {}).items():
        try:
            TYPE_COLOR[key] = discord.Color.from_str(hex_code)
        except Exception:
            TYPE_COLOR[key] = discord.Color.dark_grey()
    TYPE_COLOR.setdefault("default", discord.Color.dark_grey())


load_cardinfo()  # chargement initial


# ================================================================================
# 🎛️ View — Carte favorite
# ================================================================================
class CarteFavoriteButton(View):
    def __init__(self, carte_name: str, user: discord.User):
        super().__init__(timeout=120)
        self.carte_name = carte_name
        self.user = user

    @discord.ui.button(label="Carte favorite", style=discord.ButtonStyle.primary, emoji="⭐")
    async def add_favorite(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Ce bouton n'est pas pour toi.", ephemeral=True
            )
            return

        await get_or_create_profile(interaction.user.id, interaction.user.name)

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE profil SET cartefav = ? WHERE user_id = ?",
                (self.carte_name, str(interaction.user.id))
            )
            conn.commit()
            conn.close()
            await interaction.response.send_message(
                f"✅ **{self.carte_name}** ajoutée à tes cartes favorites !",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR SQLite CarteFavoriteButton] {e}")
            await interaction.response.send_message(
                "❌ Erreur lors de l'enregistrement.", ephemeral=True
            )


# ================================================================================
# 🔧 Helpers de formatage
# ================================================================================
def translate_card_type(type_str: str) -> str:
    """Traduit le type brut de l'API en français (match le plus long)."""
    if not type_str:
        return "Inconnu"
    t = type_str.lower().strip()
    matches = [eng for eng in TYPE_TRANSLATION if eng in t]
    if not matches:
        return type_str
    best = max(matches, key=len)
    return TYPE_TRANSLATION[best]


def pick_embed_color(type_str: str) -> discord.Color:
    if not type_str:
        return TYPE_COLOR.get("default")
    priority_keys = [
        "fusion", "ritual", "synchro", "xyz", "link",
        "pendulum", "spell", "trap", "token", "monster"
    ]
    t = type_str.lower()
    for key in priority_keys:
        if key in t and key in TYPE_COLOR:
            return TYPE_COLOR[key]
    return TYPE_COLOR.get("default")


def format_attribute(attr: str) -> str:
    return ATTRIBUT_EMOJI.get(attr.upper(), attr) if attr else "?"


def format_race(race: str, type_raw: str) -> str:
    if not race:
        return "?"
    t = type_raw.lower()
    if "spell" in t:
        return SPELL_RACE_TRANSLATION.get(race, race)
    if "trap" in t:
        return TRAP_RACE_TRANSLATION.get(race, race)
    return TYPE_EMOJI.get(race, race)


def format_frame_type(frame_type: str) -> str | None:
    if not frame_type:
        return None
    return FRAME_TYPE_TRANSLATION.get(frame_type)


def format_limit_short(value: str | None) -> str:
    """Retourne juste le nombre max autorisé en deck : '3', '2', '1' ou '0'."""
    if not value:
        return "3"
    entry = BANLIST_TRANSLATION.get(str(value).strip(), {"max": 3})
    return str(entry.get("max", 3))


def format_price(carte: dict) -> str | None:
    """Retourne une ligne de prix Cardmarket / TCGPlayer si dispo."""
    prices = carte.get("card_prices") or []
    if not prices:
        return None
    p = prices[0]
    cm = p.get("cardmarket_price")
    tcg = p.get("tcgplayer_price")
    parts = []
    if cm and cm not in ("0", "0.00", None):
        parts.append(f"🇪🇺 {cm} €")
    if tcg and tcg not in ("0", "0.00", None):
        parts.append(f"🇺🇸 {tcg} $")
    return " / ".join(parts) if parts else None


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Carte(commands.Cog):
    """Commande /ygocarte et !ygocarte — Rechercher ou tirer une carte Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _show_card(self, channel: discord.abc.Messageable, nom: str, user=None):
        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return await safe_send(channel, "❌ Session HTTP non disponible.")

        # ✅ 1 SEUL appel API
        carte = await fetch_card_full(nom, session)
        if not carte:
            if not nom or nom.lower() == "random":
                return await safe_send(channel, "❌ Impossible de tirer une carte aléatoire.")
            return await safe_send(channel, f"❌ Aucune carte trouvée pour `{nom}`.")

        # --- Extraction des champs ---------------------------------------------
        card_name_fr = carte.get("name_fr") or carte.get("name")
        card_name_en = carte.get("name")
        type_raw     = carte.get("type", "")
        frame_type   = carte.get("frameType", "")
        race         = carte.get("race", "")
        attr         = carte.get("attribute", "")
        atk          = carte.get("atk")
        defe         = carte.get("def")
        level        = carte.get("level")
        linkval      = carte.get("linkval") or carte.get("link_rating")
        desc         = carte.get("desc_fr") or carte.get("desc") or "Pas de description."
        archetype    = carte.get("archetype")
        banlist_info = carte.get("banlist_info", {}) or {}

        # misc=yes uniquement
        genesys      = carte.get("genesys_points")
        tcg_date     = carte.get("tcg_date")
        md_rarity    = carte.get("md_rarity")
        konami_id    = carte.get("konami_id")

        # --- Limites (compact sur une ligne) -----------------------------------
        tcg_limit  = format_limit_short(banlist_info.get("ban_tcg"))
        ocg_limit  = format_limit_short(banlist_info.get("ban_ocg"))
        goat_limit = format_limit_short(banlist_info.get("ban_goat"))

        # --- Header -------------------------------------------------------------
        header_lines = []
        if archetype:
            header_lines.append(f"**Archétype** : 🧬 {archetype}")

        header_lines.append(
            f"**Limites** : TCG {tcg_limit} / OCG {ocg_limit} / GOAT {goat_limit}"
        )

        if genesys is not None:
            header_lines.append(f"**Points Genesys** : 🎯 {genesys}")

        # --- Détails ------------------------------------------------------------
        card_type_fr = translate_card_type(type_raw)
        color = pick_embed_color(type_raw)
        frame_fr = format_frame_type(frame_type)

        lines = [f"**Type de carte** : {card_type_fr}"]
        if frame_fr and frame_fr.lower() not in card_type_fr.lower():
            lines.append(f"**Frame** : {frame_fr}")
        if race:
            lines.append(f"**Type (race)** : {format_race(race, type_raw)}")
        if attr:
            lines.append(f"**Attribut** : {format_attribute(attr)}")
        if linkval:
            lines.append(f"**Lien** : 🔗 {linkval}")
        elif level:
            lines.append(f"**Niveau/Rang** : ⭐ {level}")
        if atk is not None or defe is not None:
            lines.append(
                f"**ATK/DEF** : ⚔️ {atk if atk is not None else '?'} / "
                f"🛡️ {defe if defe is not None else '?'}"
            )

        lines.append(f"**Description**\n{desc}")

        # --- Infos bonus --------------------------------------------------------
        extras = []
        if tcg_date:
            extras.append(f"📅 Sortie TCG : `{tcg_date}`")
        if md_rarity:
            extras.append(f"🎮 Rareté MD : `{md_rarity}`")
        if konami_id:
            extras.append(f"🆔 Konami ID : `{konami_id}`")
        price_line = format_price(carte)
        if price_line:
            extras.append(f"💰 Prix : {price_line}")
        if extras:
            lines.append("**Infos**\n" + "\n".join(f"• {e}" for e in extras))

        # --- Embed --------------------------------------------------------------
        embed = discord.Embed(
            title=f"{card_name_fr}",
            description="\n".join(header_lines) + "\n\n" + "\n".join(lines),
            color=color
        )

        if carte.get("card_images"):
            thumb = carte["card_images"][0].get("image_url_cropped")
            if thumb:
                embed.set_thumbnail(url=thumb)

        embed.set_footer(text=f"Nom anglais : {card_name_en}")

        view = CarteFavoriteButton(card_name_en, user or channel)
        await safe_send(channel, embed=embed, view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ygocarte",
        description="Rechercher ou tirer une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT)."
    )
    @app_commands.describe(nom="Nom de la carte ou 'random'")
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_carte(self, interaction: discord.Interaction, nom: str = None):
        if not await safe_defer(interaction):
            return
        await self._show_card(interaction.channel, nom, user=interaction.user)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="ygocarte",
        aliases=["ycarte", "ygocard", "ycard"],
        help="🔍 Rechercher une carte ou tirer une carte aléatoire avec !ygocarte random."
    )
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_carte(self, ctx: commands.Context, *, nom: str = None):
        await self._show_card(ctx.channel, nom, user=ctx.author)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Carte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
