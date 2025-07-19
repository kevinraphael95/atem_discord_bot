# ────────────────────────────────────────────────────────────────────────────────
# 📌 customcard.py — Commande !customcard
# Objectif : Générer une carte 100% aléatoire et crédible, basée sur l'utilisateur
# Catégorie : Fun / Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands
import random
import hashlib
import json
import io
from utils.discord_utils import safe_send  # ou remplace par ctx.send si besoin

# ────────────────────────────────────────────────────────────────────────────────
# 🔢 Données de base chargées depuis le JSON externe
# ────────────────────────────────────────────────────────────────────────────────

with open("data/cccard.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)

ATTRIBUTES = DATA["attributes"]
RACES = DATA["races"]
TYPES = DATA["types"]
EFFECT_TEMPLATES = DATA["effect_templates"]
ACTIONS = DATA["actions"]
RESULTS = DATA["results"]
NAME_PREFIXES = DATA["name_prefixes"]
NAME_MIDDLES = DATA["name_middles"]
NAME_SUFFIXES = DATA["name_suffixes"]

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Fonction de génération déterministe
# ────────────────────────────────────────────────────────────────────────────────

def generate_custom_card(user: discord.User) -> dict:
    seed = int(hashlib.sha256(str(user.id).encode()).hexdigest(), 16)
    rng = random.Random(seed)

    name = f"{rng.choice(NAME_PREFIXES)} of {rng.choice(NAME_MIDDLES)} {rng.choice(NAME_SUFFIXES)} - {user.display_name}"

    card_type = rng.choice(TYPES)
    attribute = rng.choice(ATTRIBUTES)
    race = rng.choice(RACES)
    level = rng.randint(1, 12)
    atk = rng.randint(500, 4000)
    def_ = rng.randint(500, 4000)

    template = rng.choice(EFFECT_TEMPLATES)
    action = rng.choice(ACTIONS)
    result = rng.choice(RESULTS)
    effect = template.format(action=action, result=result)

    return {
        "name": name,
        "type": card_type,
        "attribute": attribute,
        "level": level,
        "race": race,
        "atk": atk,
        "def": def_,
        "effect": effect,
        "creator_id": user.id,
        "creator_name": user.display_name,
        "image_url": user.display_avatar.with_format("png").url
    }

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Commande Discord
# ────────────────────────────────────────────────────────────────────────────────

class CustomCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="customcard", aliases=["maCarte", "maCarteYuGiOh"])
    async def customcard(self, ctx: commands.Context, target: discord.User = None):
        """Génère une carte aléatoire et crédible basée sur un utilisateur"""
        user = target or ctx.author
        card = generate_custom_card(user)

        embed = discord.Embed(
            title=f"🃏 Carte Custom de {user.display_name}",
            color=discord.Color.dark_purple()
        )
        embed.set_thumbnail(url=card["image_url"])
        embed.add_field(name="📝 Nom", value=card["name"], inline=False)
        embed.add_field(name="🔷 Type", value=card["type"], inline=True)
        embed.add_field(name="⚡ Attribut", value=card["attribute"], inline=True)
        embed.add_field(name="🌟 Niveau", value=str(card["level"]), inline=True)
        embed.add_field(name="🐲 Race", value=card["race"], inline=True)
        embed.add_field(name="🗡️ ATK / DEF", value=f"{card['atk']} / {card['def']}", inline=True)
        embed.add_field(name="💬 Effet", value=card["effect"], inline=False)
        embed.set_footer(text=f"ID Discord : {card['creator_id']}")

        # Conversion du dict en JSON et création d'un fichier Discord utilisable
        json_data = json.dumps(card, indent=2, ensure_ascii=False)
        file_obj = io.BytesIO(json_data.encode('utf-8'))
        file = discord.File(fp=file_obj, filename="custom_card.json")

        # Envoi via safe_send pour gérer ratelimits 429
        await safe_send(ctx.channel, embed=embed, file=file)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CustomCard(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
