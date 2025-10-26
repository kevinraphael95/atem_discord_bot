# ────────────────────────────────────────────────────────────────────────────────
# 🎲 random.py — Commande !random
# Objectif : Tirer une carte Yu-Gi-Oh! aléatoire et l’afficher joliment comme !carte
# Source : API publique YGOPRODeck (https://db.ygoprodeck.com/api-guide/)
# Langue : 🇫🇷 Français prioritaire, fallback anglais
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import random

from utils.discord_utils import safe_send
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Mappages décoratifs (identiques à carte.py)
# ────────────────────────────────────────────────────────────────────────────────
ATTRIBUT_EMOJI = {
    "LIGHT": "☀️ Lumière",
    "DARK": "🌑 Ténèbres",
    "EARTH": "🌍 Terre",
    "WATER": "💧 Eau",
    "FIRE": "🔥 Feu",
    "WIND": "🌪️ Vent",
    "DIVINE": "✨ Divin"
}

TYPE_EMOJI = {
    "Aqua": "💦 Aqua",
    "Beast": "🐾 Bête",
    "Beast-Warrior": "🐺⚔️ Bête-Guerrier",
    "Winged Beast": "🦅 Bête Ailée",
    "Cyberse": "🖥️ Cyberse",
    "Fiend": "😈 Démon",
    "Dinosaur": "🦖 Dinosaure",
    "Dragon": "🐉 Dragon",
    "Fairy": "🧝 Elfe",
    "Warrior": "🗡️ Guerrier",
    "Insect": "🐛 Insecte",
    "Illusion": "🎭 Illusion",
    "Machine": "🤖 Machine",
    "Spellcaster": "🔮 Magicien",
    "Plant": "🌱 Plante",
    "Fish": "🐟 Poisson",
    "Psychic": "🧠 Psychique",
    "Pyro": "🔥 Pyro",
    "Reptile": "🦎 Reptile",
    "Rock": "🪨 Rocher",
    "Sea Serpent": "🐍 Serpent de mer",
    "Thunder": "⚡ Tonnerre",
    "Wyrm": "🐲 Wyrm",
    "Zombie": "🧟 Zombie",
    "Divine-Beast": "👑 Bête-Divine"
}

TYPE_TRANSLATION = {
    "normal monster": "Monstre Normal",
    "effect monster": "Monstre à effet",
    "fusion monster": "Monstre Fusion",
    "ritual monster": "Monstre Rituel",
    "synchro monster": "Monstre Synchro",
    "xyz monster": "Monstre Xyz",
    "link monster": "Monstre Lien",
    "pendulum monster": "Monstre Pendule",
    "spell card": "Magie",
    "trap card": "Piège",
    "skill card": "Carte Compétence",
    "token": "Jeton"
}

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
# 🧠 Cog principal — !random
# ────────────────────────────────────────────────────────────────────────────────
class Random(commands.Cog):
    """🎲 Commande !random — Tire une carte Yu-Gi-Oh! aléatoire avec affichage stylé"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="random",
        aliases=["ran", "aléatoire"],
        help="🎲 Tire une carte Yu-Gi-Oh! aléatoire (FR ou EN)."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def random_card(self, ctx: commands.Context):
        languages = ["fr", "en"]

        async with aiohttp.ClientSession() as session:
            for lang in languages:
                url = f"https://db.ygoprodeck.com/api/v7/randomcard.php?language={lang}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        carte = await resp.json()
                        langue = lang
                        break
            else:
                await safe_send(ctx, "❌ Impossible de récupérer une carte depuis l’API.")
                return

        # Données carte
        name = carte.get("name", "Carte inconnue")
        card_type_raw = carte.get("type", "")
        card_type_fr = translate_card_type(card_type_raw)
        color = pick_embed_color(card_type_raw)
        race = carte.get("race", "")
        attr = carte.get("attribute", "")
        desc = carte.get("desc", "Pas de description disponible.")
        atk = carte.get("atk")
        defe = carte.get("def")
        level = carte.get("level")
        rank = carte.get("rank")
        linkval = carte.get("linkval") or carte.get("link_rating")
        card_id = carte.get("id", "?")
        konami_id = carte.get("card_images", [{}])[0].get("id", "?")

        # Construction des lignes d’infos
        infos = [f"**Type de carte** : {card_type_fr}"]
        if race:
            infos.append(f"**Type** : {format_race(race)}")
        if attr:
            infos.append(f"**Attribut** : {format_attribute(attr)}")
        if linkval:
            infos.append(f"**Lien** : 🔗 {linkval}")
        elif rank:
            infos.append(f"**Niveau/Rang** : ⭐ {rank}")
        elif level:
            infos.append(f"**Niveau/Rang** : ⭐ {level}")
        if atk is not None or defe is not None:
            atk_txt = f"⚔️ {atk}" if atk is not None else "⚔️ ?"
            def_txt = f"🛡️ {defe}" if defe is not None else "🛡️ ?"
            infos.append(f"**ATK/DEF** : {atk_txt}/{def_txt}")
        infos.append(f"**Description**\n{desc}")

        # Embed
        embed = discord.Embed(
            title=f"**{name}**",
            description="\n".join(infos),
            color=color
        )

        if "card_images" in carte and carte["card_images"]:
            thumb = carte["card_images"][0].get("image_url_small") or carte["card_images"][0].get("image_url")
            if thumb:
                embed.set_thumbnail(url=thumb)

        embed.set_footer(text=f"ID Carte : {card_id} | ID Konami : {konami_id} | Langue : {langue.upper()}")

        view = CarteFavoriteButton(name, ctx.author)
        await safe_send(ctx.channel, embed=embed, view=view)

    def cog_load(self):
        self.random_card.category = "🃏 Yu-Gi-Oh!"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Random(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
