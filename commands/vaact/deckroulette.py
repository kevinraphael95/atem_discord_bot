# ────────────────────────────────────────────────────────────────────────────────
# 📌 deckroulette.py — Commande interactive !deckroulette
# Objectif : Proposer un deck custom aléatoire à un joueur
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
from utils.discord_utils import safe_send  # juste send car pas de menu

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des decks custom (format JSON)
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "decks.json")

def load_decks():
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class DeckRoulette(commands.Cog):
    """
    Commande !deckroulette — Propose un deck custom aléatoire à un joueur
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="deckroulette",
        help="Donne un deck custom aléatoire à jouer.",
        description="Choisit au hasard un deck dans la liste des decks custom et l'affiche."
    )
    async def deckroulette(self, ctx: commands.Context):
        try:
            decks_data = load_decks()  # On charge le JSON complet
            
            # decks_data est attendu au format dict, par exemple :
            # { "deck1": {"deck": [...], "astuces": "..."},
            #   "deck2": {...}, ... }
            
            if not decks_data:
                await safe_send(ctx.channel, "❌ Aucun deck disponible dans la base.")
                return

            deck_name = random.choice(list(decks_data.keys()))
            deck_info = decks_data[deck_name]

            deck_list = deck_info.get("deck", [])
            astuces = deck_info.get("astuces", "Aucune astuce disponible.")

            # Format du deck en liste
            if isinstance(deck_list, list):
                deck_text = "\n".join(f"• {card}" for card in deck_list)
            else:
                deck_text = str(deck_list)

            embed = discord.Embed(
                title=f"🎲 Deck aléatoire : {deck_name}",
                color=discord.Color.green()
            )
            embed.add_field(name="📘 Deck", value=deck_text, inline=False)
            embed.add_field(name="💡 Astuces", value=astuces, inline=False)

            await safe_send(ctx.channel, embed=embed)

        except Exception as e:
            print(f"[ERREUR deckroulette] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors du choix du deck.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = DeckRoulette(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
