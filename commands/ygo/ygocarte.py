# ================================================================================
# 📌 carte.py — Commande interactive !carte
# Objectif :
#   - Rechercher et afficher les détails d'une carte Yu-Gi-Oh!
#   - OU tirer une carte aléatoire avec !carte random
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 3 sec / utilisateur
# Version optimisée : 1 seul appel API par recherche
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
import urllib.parse
import sqlite3

from utils.discord_utils import safe_send
from utils.vaact_utils import DB_PATH, get_or_create_profile

# ================================================================================
# 🎨 Chargement décorations et couleurs
# ================================================================================
CARDINFO_PATH = Path("data/cardinfofr.json")
try:
    with CARDINFO_PATH.open("r", encoding="utf-8") as f:
        CARDINFO = json.load(f)
except FileNotFoundError:
    print("[ERREUR] Fichier data/cardinfofr.json introuvable.")
    CARDINFO = {}

ATTRIBUT_EMOJI         = CARDINFO.get("ATTRIBUT_EMOJI", {})
TYPE_EMOJI             = CARDINFO.get("TYPE_EMOJI", {})
TYPE_TRANSLATION       = CARDINFO.get("TYPE_TRANSLATION", {})
SPELL_RACE_TRANSLATION = CARDINFO.get("SPELL_RACE_TRANSLATION", {})
TRAP_RACE_TRANSLATION  = CARDINFO.get("TRAP_RACE_TRANSLATION", {})
TYPE_COLOR = {}
for key, hex_code in CARDINFO.get("TYPE_COLOR", {}).items():
    try:
        TYPE_COLOR[key] = discord.Color.from_str(hex_code)
    except Exception:
        TYPE_COLOR[key] = discord.Color.dark_grey()
TYPE_COLOR.setdefault("default", discord.Color.dark_grey())

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
            await interaction.response.send_message("❌ Ce bouton n'est pas pour toi.", ephemeral=True)
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
                f"✅ **{self.carte_name}** ajoutée à tes cartes favorites !", ephemeral=True
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
    if not type_str:
        return "Inconnu"
    t = type_str.lower()
    for eng, fr in TYPE_TRANSLATION.items():
        if eng in t:
            return fr
    return type_str

def pick_embed_color(type_str: str) -> discord.Color:
    if not type_str:
        return TYPE_COLOR.get("default")
    priority_keys = ["fusion","ritual","synchro","xyz","link","pendulum","spell","trap","token","monster"]
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

# ================================================================================
# 🔧 FONCTION UNIQUE : fetch la carte complète en 1 appel
# ================================================================================
async def fetch_card_full(nom: str | None, session, multi_lang: bool = True):
    """
    Récupère une carte complète en UN SEUL appel API.

    - Si `nom` est None ou "random" → carte aléatoire
    - Sinon → recherche par nom (multi-langue : fr, de, it, pt, en)

    Retourne le dict de la carte ou None.
    """
    if not nom or nom.lower() == "random":
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?random=yes&language=fr"
    else:
        nom_encode = urllib.parse.quote(nom)
        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}&language=fr"

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                # Si pas trouvé en FR, essaie sans langue (anglais)
                if nom and multi_lang:
                    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={urllib.parse.quote(nom)}"
                    async with session.get(url) as resp2:
                        if resp2.status != 200:
                            return None
                        data = await resp2.json()
                        cards = data.get("data", [])
                        return cards[0] if cards else None
                return None

            data = await resp.json()
            cards = data.get("data", [])
            return cards[0] if cards else None
    except Exception as e:
        print(f"[fetch_card_full] Erreur : {e}")
        return None

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

        # ✅ Tout est déjà dans `carte` (1 seul appel)
        card_name_fr  = carte.get("name_fr") or carte.get("name")
        card_name_en  = carte.get("name")  # Nom anglais toujours présent
        card_id       = carte.get("id")
        type_raw      = carte.get("type", "")
        race          = carte.get("race", "")
        attr          = carte.get("attribute", "")
        atk           = carte.get("atk")
        defe          = carte.get("def")
        level         = carte.get("level")
        rank          = carte.get("rank")
        linkval       = carte.get("linkval") or carte.get("link_rating")
        desc          = carte.get("desc_fr") or carte.get("desc") or "Pas de description."
        archetype     = carte.get("archetype")
        genesys       = carte.get("genesys_points")
        banlist_info  = carte.get("banlist_info", {})

        # Banlist
        tcg_limit  = banlist_info.get("ban_tcg", "Autorisé")
        ocg_limit  = banlist_info.get("ban_ocg", "Autorisé")
        goat_limit = banlist_info.get("ban_goat", "Autorisé")

        # Header
        header_lines = []
        if archetype:
            header_lines.append(f"**Archétype** : 🧬 {archetype}")
        header_lines.append(f"**Limites** : TCG {tcg_limit} / OCG {ocg_limit} / GOAT {goat_limit}")
        if genesys is not None:
            header_lines.append(f"**Points Genesys** : 🎯 {genesys}")

        # Détails
        card_type_fr = translate_card_type(type_raw)
        color = pick_embed_color(type_raw)
        lines = [f"**Type de carte** : {card_type_fr}"]
        if race:
            lines.append(f"**Type** : {format_race(race, type_raw)}")
        if attr:
            lines.append(f"**Attribut** : {format_attribute(attr)}")
        if linkval:
            lines.append(f"**Lien** : 🔗 {linkval}")
        elif rank:
            lines.append(f"**Niveau/Rang** : ⭐ {rank}")
        elif level:
            lines.append(f"**Niveau/Rang** : ⭐ {level}")
        if atk is not None or defe is not None:
            lines.append(f"**ATK/DEF** : ⚔️ {atk or '?'} / 🛡️ {defe or '?'}")
        lines.append(f"**Description**\n{desc}")

        # Embed
        embed = discord.Embed(
            title=f"**{card_name_fr}**",
            description="\n".join(header_lines) + "\n\n" + "\n".join(lines),
            color=color
        )

        if "card_images" in carte and carte["card_images"]:
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
        await interaction.response.defer()
        await self._show_card(interaction.channel, nom, user=interaction.user)
        await interaction.delete_original_response()

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
