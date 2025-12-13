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
            decks = []

            for saison, persos in data.items():
                for duelliste, infos in persos.items():
                    deck_data = infos.get("deck", {})

                    if not isinstance(deck_data, dict):
                        continue

                    for niveau, contenus in deck_data.items():
                        if isinstance(contenus, dict):
                            for type_deck, lien in contenus.items():
                                decks.append((saison, duelliste, niveau, type_deck, lien))
                        elif isinstance(contenus, str):
                            decks.append((saison, duelliste, niveau, "Deck", contenus))

            if not decks:
                return await safe_send(ctx, "❌ Aucun deck n'est disponible.")

            saison, duelliste, niveau, type_deck, lien = random.choice(decks)

            # ─ Embed stylé ─
            embed = discord.Embed(
                title="🎲 Deck Aléatoire Tiré !",
                color=discord.Color.random()
            )
            embed.add_field(
                name="👤 Duelliste",
                value=f"**{duelliste}** *(Saison {saison})*",
                inline=False
            )
            embed.add_field(name="🎚️ Niveau", value=niveau, inline=True)
            embed.add_field(name="📘 Type", value=type_deck, inline=True)
            embed.add_field(name="🔗 Deck", value=lien, inline=False)

            embed.set_footer(
                text=f"Tiré par {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
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
