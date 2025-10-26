# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif : Rechercher et afficher les détails d’une carte Yu-Gi-Oh!
# - Thumbnail (petit) en haut à droite
# - Labels en français
# - Décoration par emoji pour race & attribut
# - Recherche multi-langues
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import urllib.parse
import json
from pathlib import Path
from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Chargement du mappage décoratif depuis data/cardinfofr.json
# ────────────────────────────────────────────────────────────────────────────────
CARDINFO_PATH = Path("data/cardinfofr.json")

try:
    with CARDINFO_PATH.open("r", encoding="utf-8") as f:
        CARDINFO = json.load(f)
except FileNotFoundError:
    print("[ERREUR] Fichier data/cardinfofr.json introuvable. Vérifie le chemin.")
    CARDINFO = {"ATTRIBUT_EMOJI": {}, "TYPE_EMOJI": {}, "TYPE_TRANSLATION": {}, "TYPE_COLOR": {}}

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
        return TYPE_COLOR.get("link", TYPE_COLOR["default"])
    if "monster" in t:
        return TYPE_COLOR["monster"]
    return TYPE_COLOR["default"]

def format_attribute(attr: str) -> str:
    return ATTRIBUT_EMOJI.get(attr.upper(), attr) if attr else "?"

def format_race(race: str) -> str:
    return TYPE_EMOJI.get(race, race) if race else "?"

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fetch carte multi-langues
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_card_multilang(nom: str) -> tuple[dict, str]:
    nom_encode = urllib.parse.quote(nom)
    languages = ["fr", "de", "it", "pt", ""]  # fallback = anglais
    async with aiohttp.ClientSession() as session:
        for lang in languages:
            url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
            if lang:
                url += f"&language={lang}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        return data["data"][0], (lang or "en")
    return None, "?"

async def fetch_card_fuzzy(nom: str) -> list[str]:
    nom_encode = urllib.parse.quote(nom)
    async with aiohttp.ClientSession() as session:
        url_fuzzy = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}"
        async with session.get(url_fuzzy) as resp:
            if resp.status == 200:
                data = await resp.json()
                return [c.get("name") for c in data.get("data", [])]
    return []

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Carte(commands.Cog):
    """Commande !carte — Rechercher une carte Yu-Gi-Oh! avec embed intelligent et traduction FR"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="carte",
        aliases=["card"],
        help="🔍 Rechercher une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT).",
        description="Affiche les infos d’une carte Yu-Gi-Oh! à partir de son nom."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def carte(self, ctx: commands.Context, *, nom: str):
        # Recherche multi-langues
        carte, langue_detectee = await fetch_card_multilang(nom)
        if not carte:
            suggestions = await fetch_card_fuzzy(nom)
            if suggestions:
                suggestion_msg = "\n".join(f"• **{s}**" for s in suggestions[:3])
                await safe_send(ctx.channel, f"❌ Carte introuvable pour `{nom}`.\n🔎 Suggestions :\n{suggestion_msg}")
                return
            await safe_send(ctx.channel, f"❌ Carte introuvable. Vérifie l’orthographe exacte : `{nom}`.")
            return

        # infos cartes
        card_name = carte.get("name", "Carte inconnue")
        card_id = carte.get("id", "?")
        card_id_konami = carte.get("card_images", [{}])[0].get("id", "?") if "card_images" in carte else "?"
        card_type_raw = carte.get("type", "")
        card_race = carte.get("race", "")
        attribute = carte.get("attribute", "")
        desc = carte.get("desc", "Pas de description disponible.")
        atk = carte.get("atk")
        defe = carte.get("def")
        level = carte.get("level")
        rank = carte.get("rank")
        linkval = carte.get("linkval") or carte.get("link_rating") or carte.get("link")

        card_type_fr = translate_card_type(card_type_raw)
        color = pick_embed_color(card_type_raw)

        # construction description FR — n'afficher que les infos utiles
        lines = [f"**Type de carte** : {card_type_fr}"]
        if card_race:
            lines.append(f"**Type** : {format_race(card_race)}")
        if "monster" in card_type_raw.lower() or attribute:
            if attribute:
                lines.append(f"**Attribut** : {format_attribute(attribute)}")
        if linkval:
            lines.append(f"**Lien** : 🔗 {linkval}")
        elif rank is not None:
            lines.append(f"**Niveau/Rang** : ⭐ {rank}")
        elif level is not None:
            lines.append(f"**Niveau/Rang** : ⭐ {level}")
        if atk is not None or defe is not None:
            atk_text = f"⚔️ {atk}" if atk is not None else "⚔️ ?"
            def_text = f"🛡️ {defe}" if defe is not None else "🛡️ ?"
            lines.append(f"**ATK/DEF** : {atk_text}/{def_text}")
        lines.append(f"**Description**\n{desc}")

        embed = discord.Embed(
            title=f"**{card_name}**",
            description="\n".join(lines),
            color=color
        )

        # thumbnail uniquement
        if "card_images" in carte and carte["card_images"]:
            img = carte["card_images"][0]
            thumb = img.get("image_url_small") or img.get("image_url")
            if thumb:
                embed.set_thumbnail(url=thumb)

        # footer avec ID API, ID Konami et langue
        embed.set_footer(text=f"ID Carte : {card_id} | ID Konami : {card_id_konami} | Langue : {langue_detectee.upper()}")

        view = CarteFavoriteButton(card_name, ctx.author)
        await safe_send(ctx.channel, embed=embed, view=view)

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
