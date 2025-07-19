# ────────────────────────────────────────────────────────────────────────────────
# 📌 avatarcard.py — Commande interactive !avatarcard
# Objectif : Crée une fausse carte Yu-Gi-Oh unique et amusante à partir d’un avatar
# Catégorie : Yu-Gi-Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands
import random
import json
import os
from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Chargement des données
# ────────────────────────────────────────────────────────────────────────────────

DATA_JSON_PATH = os.path.join("data", "avatarcard_data.json")

def load_data():
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🧪 Génération d'une carte à partir d'un ID membre
# ────────────────────────────────────────────────────────────────────────────────

def generate_avatar_card(member_id, data):
    random.seed(member_id)  # Stable par utilisateur

    name = random.choice(data["noms"])
    card_type = random.choice(["Monstre Normal", "Monstre à Effet", "Synchro", "Xyz", "Link", "Pendule"])
    monster_type = random.choice(data["types"])
    level = random.randint(1, 12)
    atk = random.randint(500, 3000)
    defe = random.randint(500, 3000)
    effet = random.choice(data["effets"]) if "Effet" in card_type else "Un monstre légendaire issu d’une autre dimension."
    attribut = random.choice(["LUMIÈRE", "TÉNÈBRES", "EAU", "FEU", "VENT", "TERRE", "DIVIN"])
    rareté = random.choice(["Commun", "Rare", "Super Rare", "Ultra Rare", "Secret Rare"])

    if card_type == "Xyz":
        niveau_label = f"Rang {level}"
    elif card_type == "Link":
        link = random.randint(1, 5)
        niveau_label = f"Lien {link}"
        defe = 0  # Les Link n'ont pas de DEF
    else:
        niveau_label = f"Niveau {level}"

    return {
        "name": name,
        "type": card_type,
        "monster_type": monster_type,
        "niveau": niveau_label,
        "atk": atk,
        "def": defe,
        "effet": effet,
        "attribut": attribut,
        "rareté": rareté
    }

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class AvatarCard(commands.Cog):
    """
    Commande !avatarcard — Crée une fausse carte Yu-Gi-Oh! à partir de l’avatar
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_data()

    @commands.command(
        name="avatarcard",
        help="Crée une carte Yu-Gi-Oh fictive avec ton avatar.",
        description="Utilise ton avatar Discord comme image de carte, avec un effet aléatoire."
    )
    async def avatarcard(self, ctx: commands.Context, membre: discord.Member = None):
        membre = membre or ctx.author

        try:
            card = generate_avatar_card(membre.id, self.data)

            embed = discord.Embed(
                title=f"🃏 Carte de {membre.display_name}",
                description=f"**{card['name']}** — *{card['type']}*",
                color=discord.Color.dark_red()
            )
            embed.add_field(name="Type", value=f"{card['monster_type']} / {card['niveau']}", inline=False)
            embed.add_field(name="Attribut", value=card["attribut"], inline=True)
            embed.add_field(name="Rareté", value=card["rareté"], inline=True)
            embed.add_field(name="ATK / DEF", value=f"{card['atk']} / {card['def']}", inline=False)
            embed.add_field(name="Effet", value=card['effet'], inline=False)
            embed.set_thumbnail(url=membre.display_avatar.url)

            await safe_send(ctx.channel, embed=embed)

        except Exception as e:
            print(f"[ERREUR avatarcard] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors de la création de la carte.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot):
    cog = AvatarCard(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Yu-Gi-Oh"
    await bot.add_cog(cog)
