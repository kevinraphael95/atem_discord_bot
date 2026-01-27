# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif :
#   - Rechercher et afficher les détails d’une carte Yu-Gi-Oh!
#   - OU tirer une carte aléatoire avec !carte random
#   - Utilise utils/card_utils pour toutes les requêtes API
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 3 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
from pathlib import Path

from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase
from utils.card_utils import search_card, fetch_random_card

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Chargement décorations et couleurs
# ────────────────────────────────────────────────────────────────────────────────
CARDINFO_PATH = Path("data/cardinfofr.json")
try:
    with CARDINFO_PATH.open("r", encoding="utf-8") as f:
        CARDINFO = json.load(f)
except FileNotFoundError:
    print("[ERREUR] Fichier data/cardinfofr.json introuvable.")
    CARDINFO = {}

ATTRIBUT_EMOJI = CARDINFO.get("ATTRIBUT_EMOJI", {})
TYPE_EMOJI = CARDINFO.get("TYPE_EMOJI", {})
TYPE_TRANSLATION = CARDINFO.get("TYPE_TRANSLATION", {})
SPELL_RACE_TRANSLATION = CARDINFO.get("SPELL_RACE_TRANSLATION", {})
TRAP_RACE_TRANSLATION = CARDINFO.get("TRAP_RACE_TRANSLATION", {})
TYPE_COLOR = {}
for key, hex_code in CARDINFO.get("TYPE_COLOR", {}).items():
    try:
        TYPE_COLOR[key] = discord.Color.from_str(hex_code)
    except Exception:
        TYPE_COLOR[key] = discord.Color.dark_grey()
TYPE_COLOR.setdefault("default", discord.Color.dark_grey())

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Carte favorite
# ────────────────────────────────────────────────────────────────────────────────
class CarteFavoriteButton(View):
    def __init__(self, carte_name: str, user: discord.User):
        super().__init__(timeout=120)
        self.carte_name = carte_name
        self.user = user

    @discord.ui.button(label="Carte favorite", style=discord.ButtonStyle.primary, emoji="⭐")
    async def add_favorite(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Ce bouton n’est pas pour toi.", ephemeral=True)
            return
        try:
            supabase.table("profil").upsert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "cartefav": self.carte_name
            }, on_conflict="user_id").execute()
            await interaction.response.send_message(
                f"✅ **{self.carte_name}** ajoutée à tes cartes favorites !", ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR Supabase] {e}")
            await interaction.response.send_message("❌ Erreur lors de l’ajout à Supabase.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Helpers pour formatage
# ────────────────────────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Carte(commands.Cog):
    """Commande /carte et !carte — Rechercher ou tirer une carte Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _show_card(self, channel: discord.abc.Messageable, nom: str, user=None):
        if not nom or nom.lower() == "random":
            carte, langue = await fetch_random_card(self.bot.aiohttp_session)
            if not carte:
                await safe_send(channel, "❌ Impossible de tirer une carte aléatoire depuis l’API.")
                return
        else:
            carte, langue, message = await search_card(nom, self.bot.aiohttp_session)
            if message:
                await safe_send(channel, message)
                return
            if not carte:
                await safe_send(channel, f"❌ Aucune carte trouvée pour `{nom}`.")
                return

        # Infos carte
        card_name = carte.get("name", "Carte inconnue")
        type_raw = carte.get("type", "")
        race = carte.get("race", "")
        attr = carte.get("attribute", "")
        atk = carte.get("atk")
        defe = carte.get("def")
        level = carte.get("level")
        rank = carte.get("rank")
        linkval = carte.get("linkval") or carte.get("link_rating")
        desc = carte.get("desc", "Pas de description disponible.")
        archetype = carte.get("archetype")
        banlist_info = carte.get("banlist_info", {})
        genesys_points = carte.get("genesys_points")

        # Limites
        def format_limit(val):
            mapping = {"Banned":"0","Limited":"1","Semi-Limited":"2","3":"3","Unlimited":"3"}
            return mapping.get(val, "3")
        tcg_limit = format_limit(banlist_info.get("ban_tcg"))
        ocg_limit = format_limit(banlist_info.get("ban_ocg"))
        goat_limit = format_limit(banlist_info.get("ban_goat"))

        header_lines = []
        if archetype:
            header_lines.append(f"**Archétype** : 🧬 {archetype}")
        header_lines.append(f"**Limites** : TCG {tcg_limit} / OCG {ocg_limit} / GOAT {goat_limit}")
        if genesys_points is not None:
            header_lines.append(f"**Points Genesys** : 🎯 {genesys_points}")

        card_type_fr = translate_card_type(type_raw)
        color = pick_embed_color(type_raw)
        lines = [f"**Type de carte** : {card_type_fr}"]
        if race: lines.append(f"**Type** : {format_race(race, type_raw)}")
        if attr: lines.append(f"**Attribut** : {format_attribute(attr)}")
        if linkval: lines.append(f"**Lien** : 🔗 {linkval}")
        elif rank: lines.append(f"**Niveau/Rang** : ⭐ {rank}")
        elif level: lines.append(f"**Niveau/Rang** : ⭐ {level}")
        if atk is not None or defe is not None:
            lines.append(f"**ATK/DEF** : ⚔️ {atk or '?'} / 🛡️ {defe or '?'}")
        lines.append(f"**Description**\n{desc}")

        embed = discord.Embed(title=f"**{card_name}**", description="\n".join(header_lines)+"\n\n"+"\n".join(lines), color=color)
        if "card_images" in carte and carte["card_images"]:
            thumb = carte["card_images"][0].get("image_url_cropped")
            if thumb: embed.set_thumbnail(url=thumb)

        view = CarteFavoriteButton(card_name, user or channel)
        await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="carte",
        description="Rechercher ou tirer une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT)."
    )
    @app_commands.describe(nom="Nom de la carte ou 'random'")
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_carte(self, interaction: discord.Interaction, nom: str = None):
        await interaction.response.defer()
        await self._show_card(interaction.channel, nom, user=interaction.user)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="carte", aliases=["card"], help="🔍 Rechercher une carte ou tirer une carte aléatoire avec !carte random.")
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_carte(self, ctx: commands.Context, *, nom: str = None):
        await self._show_card(ctx.channel, nom, user=ctx.author)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Carte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
