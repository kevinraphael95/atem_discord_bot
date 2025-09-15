# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif : Rechercher et afficher les détails d’une carte Yu-Gi-Oh! avec embed intelligent
# - Thumbnail (petit) en haut à droite
# - Labels en français
# - Décoration par emoji pour race & attribut
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
from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase  # utilisé pour favoris si besoin

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Mappages (faciles à modifier)
# ────────────────────────────────────────────────────────────────────────────────
# Emojis pour attributs (les clés correspondent aux valeurs renvoyées par l'API)
ATTRIBUT_EMOJI = {
    "LIGHT": "☀️ Lumière",
    "DARK": "🌑 Ténèbres",
    "EARTH": "🌍 Terre",
    "WATER": "💧 Eau",
    "FIRE": "🔥 Feu",
    "WIND": "🌪️ Vent",
    "DIVINE": "✨ Divin"
}

# Emoji par race/type de monstre (clé = valeur 'race' de l'API)
TYPE_EMOJI = {
    "Aqua": "💦 Aqua", "Beast": "🐾 Bête", "Beast-Warrior": "🐺⚔️ Bête-Guerrier",
    "Winged Beast": "🦅 Bête Ailée", "Cyberse": "🖥️ Cyberse", "Fiend": "😈 Démon",
    "Dinosaur": "🦖 Dinosaure", "Dragon": "🐉 Dragon", "Fairy": "🧝 Elfe",
    "Warrior": "🗡️ Guerrier", "Insect": "🐛 Insecte", "Illusion": "🎭 Illusion",
    "Machine": "🤖 Machine", "Spellcaster": "🔮 Magicien", "Plant": "🌱 Plante",
    "Fish": "🐟 Poisson", "Psychic": "🧠 Psychique", "Pyro": "🔥 Pyro",
    "Reptile": "🦎 Reptile", "Rock": "🪨 Rocher", "Sea Serpent": "🐍 Serpent de mer",
    "Thunder": "⚡ Tonnerre", "Wyrm": "🐲 Wyrm", "Zombie": "🧟 Zombie",
    "Divine-Beast": "👑 Bête-Divine"
}

# Traduction des types de carte (matching large, anglais -> français)
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

# Couleurs d'embed selon type (matching sur l'anglais renvoyé par l'API)
TYPE_COLOR = {
    "monster": discord.Color.red(),
    "spell": discord.Color.green(),
    "trap": discord.Color.blue(),
    "link": discord.Color.purple(),
    # fallback
    "default": discord.Color.dark_grey()
}

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — bouton "Carte favorite" (optionnel)
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
# 🔧 Helpers : traduction & extraction d'infos utiles
# ────────────────────────────────────────────────────────────────────────────────
def translate_card_type(type_str: str) -> str:
    if not type_str:
        return "Inconnu"
    t = type_str.lower()
    # prioritize longer/compound matches
    for eng, fr in TYPE_TRANSLATION.items():
        if eng in t:
            return fr
    # fallback: capitalize original
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
    if not attr:
        return "?"
    return ATTRIBUT_EMOJI.get(attr.upper(), attr)

def format_race(race: str) -> str:
    if not race:
        return "?"
    return TYPE_EMOJI.get(race, race)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Carte(commands.Cog):
    """
    Commande !carte — Rechercher une carte Yu-Gi-Oh! et afficher ses informations.
    Embed intelligent selon le type de carte, labels en français, thumbnail only.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="carte",
        aliases=["card"],
        help="🔍 Rechercher une carte Yu-Gi-Oh! (FR/EN).",
        description="Affiche les infos d’une carte Yu-Gi-Oh! à partir de son nom (FR, EN)."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def carte(self, ctx: commands.Context, *, nom: str):
        nom_encode = urllib.parse.quote(nom)
        carte = None
        nom_corrige = nom

        try:
            async with aiohttp.ClientSession() as session:
                # recherche directe (nom exact)
                url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "data" in data and len(data["data"]) > 0:
                            carte = data["data"][0]
                            nom_corrige = carte.get("name", nom)

                # fuzzy si pas trouvé
                if not carte:
                    url_fuzzy = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}"
                    async with session.get(url_fuzzy) as resp_fuzzy:
                        if resp_fuzzy.status == 200:
                            data_fuzzy = await resp_fuzzy.json()
                            suggestions = data_fuzzy.get("data", [])
                            if suggestions:
                                noms = [c.get("name") for c in suggestions[:3]]
                                suggestion_msg = "\n".join(f"• **{n}**" for n in noms)
                                await safe_send(ctx.channel, f"❌ Carte introuvable pour `{nom}`.\n🔎 Suggestions :\n{suggestion_msg}")
                                return
        except Exception as e:
            print(f"[ERREUR carte] {e}")
            await safe_send(ctx.channel, "🚨 Une erreur est survenue lors de la recherche.")
            return

        if not carte:
            await safe_send(ctx.channel, f"❌ Carte introuvable. Vérifie l’orthographe exacte : `{nom}`.")
            return

        # indique nom corrigé si différent
        if nom_corrige.lower() != nom.lower():
            await safe_send(ctx.channel, f"🔍 Résultat trouvé pour **{nom_corrige}**")

        # extraction des champs courants
        card_name = carte.get("name", "Carte inconnue")
        card_id = carte.get("id", "?")
        card_type_raw = carte.get("type", "")         # ex: "Effect Monster" ou "Spell Card"
        card_race = carte.get("race", "")             # ex: "Dragon"
        attribute = carte.get("attribute", "")        # ex: "LIGHT"
        desc = carte.get("desc", "Pas de description disponible.")
        atk = carte.get("atk")
        defe = carte.get("def")
        level = carte.get("level")
        rank = carte.get("rank")
        linkval = carte.get("linkval") or carte.get("link_rating") or carte.get("link")

        # traduction & couleur
        card_type_fr = translate_card_type(card_type_raw)
        color = pick_embed_color(card_type_raw)

        # construction description FR — n'afficher que les infos utiles
        lines = []

        # Type de carte (FR)
        lines.append(f"**Type de carte** : {card_type_fr}")

        # Race / Type (avec emoji si connu)
        if card_race:
            lines.append(f"**Type** : {format_race(card_race)}")
        # Attribut (pour monstres)
        if "monster" in card_type_raw.lower() or attribute:
            if attribute:
                lines.append(f"**Attribut** : {format_attribute(attribute)}")
        # Niveau / Rang / Lien
        # on affiche la première valeur disponible dans: linkval -> rank -> level
        if linkval:
            lines.append(f"**Lien** : 🔗 {linkval}")
        elif rank is not None:
            lines.append(f"**Niveau/Rang** : ⭐ {rank}")
        elif level is not None:
            lines.append(f"**Niveau/Rang** : ⭐ {level}")

        # ATK / DEF (monstres uniquement)
        if atk is not None or defe is not None:
            atk_text = f"⚔️ {atk}" if atk is not None else "⚔️ ?"
            def_text = f"🛡️ {defe}" if defe is not None else "🛡️ ?"
            lines.append(f"**ATK/DEF** : {atk_text}/{def_text}")

        # Description (toujours)
        lines.append(f"**Description**\n{desc}")

        # création embed — thumbnail uniquement (pas d'image pleine)
        embed = discord.Embed(
            title=f"**{card_name}**",
            description="\n".join(lines),
            color=color
        )

        # thumbnail (petite image à droite)
        if "card_images" in carte and carte["card_images"]:
            img = carte["card_images"][0]
            thumb = img.get("image_url_small") or img.get("image_url")
            if thumb:
                embed.set_thumbnail(url=thumb)

        # footer avec ID carte
        embed.set_footer(text=f"ID Carte : {card_id}")

        # bouton favoris
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
