# ────────────────────────────────────────────────────────────────────────────────
# 📌 randeck.py — Commande interactive !randeck
# Objectif : Tirer un deck custom aléatoire à jouer
# Catégorie : VAACT
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import json
import os
import random
from utils.discord_utils import safe_send  # ✅ Utilisation des safe_

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "deck_data.json")

def load_data():
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Randeck(commands.Cog):
    """
    Commande !randeck — Tire un deck aléatoire à jouer
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="randeck",
        aliases=["deckroulette"],
        help="Tire un deck custom aléatoire à jouer.",
        description="Choisis un deck aléatoire parmi tous les decks custom enregistrés."
    )
    async def randeck(self, ctx: commands.Context):
        """Commande principale pour afficher un deck random."""
        try:
            data = load_data()
            personnages = []

            for saison in data.values():
                for perso, infos in saison.items():
                    if "deck" in infos and infos["deck"]:
                        personnages.append((perso, infos))

            if not personnages:
                return await safe_send(ctx, "❌ Aucun deck n'est disponible.")

            nom, infos = random.choice(personnages)
            lien_deck = random.choice(infos["deck"])

            embed = discord.Embed(
                title=f"🎲 Deck aléatoire : {nom}",
                description=f"[Voir le deck ici]({lien_deck})",
                color=discord.Color.random()
            )

            await safe_send(ctx.channel, embed=embed)

        except Exception as e:
            print(f"[ERREUR randeck] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors du tirage du deck.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Randeck(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
