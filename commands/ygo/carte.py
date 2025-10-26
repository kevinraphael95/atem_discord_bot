# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif :
#   - Rechercher et afficher les détails d’une carte Yu-Gi-Oh!
#   - OU tirer une carte aléatoire avec !carte random
# - Thumbnail en haut à droite
# - Labels en français
# - Décoration par emoji (race & attribut)
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
import random
from pathlib import Path
from utils.discord_utils import safe_send
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
# 🔧 Fetch carte (multi-langue, fuzzy & random)
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_card_multilang(nom: str) -> tuple[dict, str]:
    nom_encode = urllib.parse.quote(nom)
    languages = ["fr", "de", "it", "pt", ""]
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

async def fetch_card_fuzzy(nom: str) -> list[dict]:
    nom_encode = urllib.parse.quote(nom)
    async with aiohttp.ClientSession() as session:
        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}&language=fr"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", [])
    return []

async def fetch_random_card() -> tuple[dict, str]:
    """Récupère une carte aléatoire en français (fallback anglais)."""
    async with aiohttp.ClientSession() as session:
        for lang in ["fr", "en"]:
            async with session.get(f"https://db.ygoprodeck.com/api/v7/randomcard.php?language={lang}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Normalisation : uniformiser le format avec cardinfo
                    if "data" in data:
                        data = data["data"][0]
                    return data, lang
    return None, "?"

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
                await safe_send(ctx.channel, "❌ Impossible de tirer une carte aléatoire depuis l’API.")
                return
        else:
            # ── Recherche classique multi-langues ────────────────────────────────
            carte, langue = await fetch_card_multilang(nom)
            if not carte:
                fuzzy_data = await fetch_card_fuzzy(nom)
                if fuzzy_data:
                    carte = fuzzy_data[0]
                    langue = "fr"
                else:
                    # si aucune carte trouvée, fallback sur une carte aléatoire
                    carte, langue = await fetch_random_card()
                    if not carte:
                        await safe_send(ctx.channel, f"❌ Carte introuvable pour `{nom}` et impossible d’en proposer une similaire.")
                        return
                    await safe_send(ctx.channel, f"❌ Carte introuvable pour `{nom}`. 🔄 Voici une carte aléatoire à la place :")

        # ── Infos carte ──────────────────────────────────────────────────────────
        card_name = carte.get("name", "Carte inconnue")
        card_id = carte.get("id", "?")
        konami_id = carte.get("card_images", [{}])[0].get("id", "?")
        type_raw = carte.get("type", "")
        race = carte.get("race", "")
        attr = carte.get("attribute", "")
        desc = carte.get("desc", "Pas de description disponible.")
        atk = carte.get("atk")
        defe = carte.get("def")
        level = carte.get("level")
        rank = carte.get("rank")
        linkval = carte.get("linkval") or carte.get("link_rating")

        card_type_fr = translate_card_type(type_raw)
        color = pick_embed_color(type_raw)

        # ── Construction des infos affichées ─────────────────────────────────────
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

        embed = discord.Embed(
            title=f"**{card_name}**",
            description="\n".join(lines),
            color=color
        )

        # ── Thumbnail ────────────────────────────────────────────────────────────
        if "card_images" in carte and carte["card_images"]:
            thumb = carte["card_images"][0].get("image_url_small") or carte["card_images"][0].get("image_url")
            if thumb:
                embed.set_thumbnail(url=thumb)

        embed.set_footer(text=f"ID Carte : {card_id} | ID Konami : {konami_id} | Langue : {langue.upper()}")

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
