# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif :
#   - Rechercher et afficher les détails d’une carte Yu-Gi-Oh!
#   - OU tirer une carte aléatoire avec !carte random
#   - Utilise utils/card_utils pour toutes les requêtes API
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import json
from pathlib import Path

from utils.discord_utils import safe_send
from utils.supabase_client import supabase
from utils.card_utils import search_card, fetch_random_card  # ✅ Import centralisé

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Chargement du mappage décoratif depuis data/cardinfofr.json
# ────────────────────────────────────────────────────────────────────────────────
CARDINFO_PATH = Path("data/cardinfofr.json")

try:
    with CARDINFO_PATH.open("r", encoding="utf-8") as f:
        CARDINFO = json.load(f)
except FileNotFoundError:
    print("[ERREUR] Fichier data/cardinfofr.json introuvable. Vérifie le chemin.")
    CARDINFO = {"ATTRIBUT_EMOJI": {}, "TYPE_EMOJI": {}, "TYPE_TRANSLATION": {}}

ATTRIBUT_EMOJI = CARDINFO.get("ATTRIBUT_EMOJI", {})
TYPE_EMOJI = CARDINFO.get("TYPE_EMOJI", {})
TYPE_TRANSLATION = CARDINFO.get("TYPE_TRANSLATION", {})

TYPE_COLOR = {
    "monster": discord.Color.red(),
    "spell": discord.Color.green(),
    "trap": discord.Color.blue(),
    "link": discord.Color.purple(),
    "default": discord.Color.dark_grey()
}

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — bouton "Carte favorite"
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
            supabase.table("favorites").delete().eq("user_id", str(interaction.user.id)).execute()
            supabase.table("favorites").insert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "cartefav": self.carte_name
            }).execute()
            await interaction.response.send_message(f"✅ **{self.carte_name}** ajoutée à tes cartes favorites !", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR Supabase] {e}")
            await interaction.response.send_message("❌ Erreur lors de l’ajout à Supabase.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Helpers
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
        return TYPE_COLOR["default"]
    t = type_str.lower()
    if "spell" in t:
        return TYPE_COLOR["spell"]
    if "trap" in t:
        return TYPE_COLOR["trap"]
    if "link" in t:
        return TYPE_COLOR["link"]
    if "monster" in t:
        return TYPE_COLOR["monster"]
    return TYPE_COLOR["default"]

def format_attribute(attr: str) -> str:
    return ATTRIBUT_EMOJI.get(attr.upper(), attr) if attr else "?"

def format_race(race: str) -> str:
    return TYPE_EMOJI.get(race, race) if race else "?"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Carte(commands.Cog):
    """Commande !carte — Rechercher ou tirer une carte Yu-Gi-Oh! aléatoire"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="carte",
        aliases=["card"],
        help="🔍 Rechercher une carte Yu-Gi-Oh! ou tirer une carte aléatoire avec `!carte random`.",
        description="Affiche les infos d’une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT)."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def carte(self, ctx: commands.Context, *, nom: str = None):
        # ── Mode aléatoire ────────────────────────────────────────────────────────
        if not nom or nom.lower() == "random":
            carte, langue = await fetch_random_card()
            if not carte:
                await safe_send(ctx, "❌ Impossible de tirer une carte aléatoire depuis l’API.")
                return
        else:
            # ── Recherche classique via utils/card_utils ─────────────────────────
            carte, langue, message = await search_card(nom)
            if message:
                await safe_send(ctx, message)
                return
            if not carte:
                await safe_send(ctx, f"❌ Aucune carte trouvée pour `{nom}`.")
                return

        # ── Infos carte ──────────────────────────────────────────────────────────
        card_name = carte.get("name", "Carte inconnue")
        card_id = carte.get("id", "?")
        konami_id = carte.get("konami_id", "?")
        type_raw = carte.get("type", "")
        race = carte.get("race", "")
        attr = carte.get("attribute", "")
        desc = carte.get("desc", "Pas de description disponible.")
        atk = carte.get("atk")
        defe = carte.get("def")
        level = carte.get("level")
        rank = carte.get("rank")
        linkval = carte.get("linkval") or carte.get("link_rating")

        # ── Section Archétype / Limites / Genesys ────────────────────────────────
        archetype = carte.get("archetype")
        banlist_info = carte.get("banlist_info", {})
        genesys_points = carte.get("genesys_points")

        def format_limit(val):
            mapping = {
                "Banned": "0",
                "Limited": "1",
                "Semi-Limited": "2",
                "3": "3",
                "Unlimited": "3"
            }
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

        # ── Partie principale de la carte ────────────────────────────────────────
        card_type_fr = translate_card_type(type_raw)
        color = pick_embed_color(type_raw)

        lines = [f"**Type de carte** : {card_type_fr}"]
        if race:
            lines.append(f"**Type** : {format_race(race)}")
        if attr:
            lines.append(f"**Attribut** : {format_attribute(attr)}")
        if linkval:
            lines.append(f"**Lien** : 🔗 {linkval}")
        elif rank:
            lines.append(f"**Niveau/Rang** : ⭐ {rank}")
        elif level:
            lines.append(f"**Niveau/Rang** : ⭐ {level}")
        if atk is not None or defe is not None:
            atk_text = f"⚔️ {atk}" if atk is not None else "⚔️ ?"
            def_text = f"🛡️ {defe}" if defe is not None else "🛡️ ?"
            lines.append(f"**ATK/DEF** : {atk_text}/{def_text}")
        lines.append(f"**Description**\n{desc}")

        # ── Embed final ──────────────────────────────────────────────────────────
        embed = discord.Embed(
            title=f"**{card_name}**",
            description="\n".join(header_lines) + "\n\n" + "\n".join(lines),
            color=color
        )

        if "card_images" in carte and carte["card_images"]:
            thumb = carte["card_images"][0].get("image_url_cropped")
            if thumb:
                embed.set_thumbnail(url=thumb)

        embed.set_footer(text=f"ID Carte : {card_id} | ID Konami : {konami_id} | Langue : {langue.upper()}")

        view = CarteFavoriteButton(card_name, ctx.author)
        await safe_send(ctx, embed=embed, view=view)

    def cog_load(self):
        self.carte.category = "🃏 Yu-Gi-Oh!"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Carte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
