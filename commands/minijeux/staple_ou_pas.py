# ────────────────────────────────────────────────────────────────────────────────
# 📌 staple_ou_pas.py — Commande interactive /staple_ou_pas et !staple_ou_pas
# Objectif :
#   - Tire une carte aléatoire (50 % de chance d’être une staple)
#   - L’utilisateur doit deviner si c’est une staple ou non
#   - L’affichage suit le même format que !carte
#   - Le résultat s’affiche directement dans l’embed
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import random
from pathlib import Path
import json

from utils.discord_utils import safe_send, safe_respond
from utils.card_utils import fetch_random_card

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Chargement des décorations de cartes (identique à carte.py)
# ────────────────────────────────────────────────────────────────────────────────
CARDINFO_PATH = Path("data/cardinfofr.json")
try:
    with CARDINFO_PATH.open("r", encoding="utf-8") as f:
        CARDINFO = json.load(f)
except FileNotFoundError:
    print("[ERREUR] Fichier data/cardinfofr.json introuvable.")
    CARDINFO = {"ATTRIBUT_EMOJI": {}, "TYPE_EMOJI": {}, "TYPE_TRANSLATION": {}}

ATTRIBUT_EMOJI = CARDINFO.get("ATTRIBUT_EMOJI", {})
TYPE_EMOJI = CARDINFO.get("TYPE_EMOJI", {})
TYPE_TRANSLATION = CARDINFO.get("TYPE_TRANSLATION", {})
SPELL_RACE_TRANSLATION = CARDINFO.get("SPELL_RACE_TRANSLATION", {})
TRAP_RACE_TRANSLATION = CARDINFO.get("TRAP_RACE_TRANSLATION", {})
TYPE_COLOR = {k: discord.Color.from_str(v) for k, v in CARDINFO.get("TYPE_COLOR", {}).items()} if "TYPE_COLOR" in CARDINFO else {}
if "default" not in TYPE_COLOR:
    TYPE_COLOR["default"] = discord.Color.dark_grey()

# ────────────────────────────────────────────────────────────────────────────────
# 🔗 URLs API
# ────────────────────────────────────────────────────────────────────────────────
STAPLES_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes&language=fr"

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Helpers visuels
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
        return TYPE_COLOR.get("default", discord.Color.dark_grey())
    t = type_str.lower()
    for key in ["fusion","ritual","synchro","xyz","link","pendulum","spell","trap","token","monster"]:
        if key in t and key in TYPE_COLOR:
            return TYPE_COLOR[key]
    return TYPE_COLOR.get("default", discord.Color.dark_grey())

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
# 🎮 View — Boutons de réponse
# ────────────────────────────────────────────────────────────────────────────────
class GuessView(discord.ui.View):
    def __init__(self, is_staple: bool, embed: discord.Embed, user: discord.User):
        super().__init__(timeout=15)
        self.is_staple = is_staple
        self.embed = embed
        self.user = user
        self.answered = False

    async def handle_guess(self, interaction: discord.Interaction, guess: bool):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Ce n’est pas ton tour !", ephemeral=True)
        if self.answered:
            return await interaction.response.send_message("⏳ Tu as déjà répondu.", ephemeral=True)
        self.answered = True

        correct = (guess == self.is_staple)
        color = discord.Color.green() if correct else discord.Color.red()
        result_text = "✅ **Bonne réponse !**" if correct else "❌ **Mauvaise réponse !**"
        true_text = "💎 Cette carte **est une Staple !**" if self.is_staple else "🪨 Cette carte **n’est pas une Staple.**"

        self.embed.color = color
        self.embed.add_field(name="Résultat", value=f"{result_text}\n{true_text}", inline=False)
        self.embed.set_footer(text="Fin de la manche")
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="Staple", style=discord.ButtonStyle.success, emoji="💎")
    async def guess_staple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_guess(interaction, True)

    @discord.ui.button(label="Pas Staple", style=discord.ButtonStyle.danger, emoji="🪨")
    async def guess_not_staple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_guess(interaction, False)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class StapleOuPas(commands.Cog):
    """Commande /staple_ou_pas et !staple_ou_pas — Devine si la carte est une staple ou pas"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = bot.aiohttp_session  # ✅ session globale du bot

    async def get_random_staple(self):
        async with self.session.get(STAPLES_API) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            cards = data.get("data", [])
            return random.choice(cards) if cards else None

    async def get_random_card(self):
        card, lang = await fetch_random_card()
        if card and lang == "en":
            async with self.session.get(f"https://db.ygoprodeck.com/api/v7/cardinfo.php?id={card['id']}&language=fr") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        return data["data"][0]
        return card

    async def build_card_embed(self, card: dict) -> discord.Embed:
        name = card.get("name", "Carte inconnue")
        type_raw = card.get("type", "")
        color = pick_embed_color(type_raw)
        race = card.get("race", "")
        attr = card.get("attribute", "")
        atk, defe = card.get("atk"), card.get("def")
        desc = card.get("desc", "Pas de description disponible.")
        level, rank, linkval = card.get("level"), card.get("rank"), card.get("linkval") or card.get("link_rating")
        archetype = card.get("archetype")

        header = [f"**Archétype** : 🧬 {archetype}"] if archetype else []

        lines = [f"**Type de carte** : {translate_card_type(type_raw)}"]
        if race: lines.append(f"**Type** : {format_race(race, type_raw)}")
        if attr: lines.append(f"**Attribut** : {format_attribute(attr)}")
        if linkval: lines.append(f"**Lien** : 🔗 {linkval}")
        elif rank: lines.append(f"**Niveau/Rang** : ⭐ {rank}")
        elif level: lines.append(f"**Niveau/Rang** : ⭐ {level}")
        if atk is not None or defe is not None:
            atk_text = f"⚔️ {atk}" if atk is not None else "⚔️ ?"
            def_text = f"🛡️ {defe}" if defe is not None else "🛡️ ?"
            lines.append(f"**ATK/DEF** : {atk_text}/{def_text}")
        lines.append(f"**Description**\n{desc}")

        embed = discord.Embed(
            title=f"**{name}**",
            description="\n".join(header) + "\n\n" + "\n".join(lines),
            color=color
        )
        if "card_images" in card and card["card_images"]:
            thumb = card["card_images"][0].get("image_url_cropped") or card["card_images"][0].get("image_url")
            if thumb:
                embed.set_thumbnail(url=thumb)
        embed.set_footer(text="💭 Devine si cette carte est une Staple ou non !")
        return embed

    async def play_round(self, ctx_or_inter, is_slash: bool):
        is_staple = random.choice([True, False])
        card = await (self.get_random_staple() if is_staple else self.get_random_card())
        if not card:
            msg = "❌ Impossible de tirer une carte."
            return await (safe_respond(ctx_or_inter, msg) if is_slash else safe_send(ctx_or_inter, msg))

        embed = await self.build_card_embed(card)
        view = GuessView(is_staple, embed, ctx_or_inter.user if is_slash else ctx_or_inter.author)
        await (safe_respond(ctx_or_inter, embed=embed, view=view) if is_slash else safe_send(ctx_or_inter, embed=embed, view=view))

    @app_commands.command(name="staple_ou_pas", description="Devine si la carte tirée est une staple ou pas !")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_staple_ou_pas(self, interaction: discord.Interaction):
        await self.play_round(interaction, True)

    @commands.command(name="staple_ou_pas", aliases=["sop"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_staple_ou_pas(self, ctx: commands.Context):
        await self.play_round(ctx, False)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = StapleOuPas(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
