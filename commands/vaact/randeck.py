# ────────────────────────────────────────────────────────────────────────────────
# 📌 randeck.py — Commande interactive !randeck
# Objectif : Tirer un deck custom aléatoire à jouer avec boutons pour tous les liens
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
    Commande !randeck — Tire un deck aléatoire et affiche tous les liens avec des boutons
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="randeck",
        aliases=["deckroulette"],
        help="Tire un deck custom aléatoire à jouer.",
        description="Choisit un deck aléatoire et affiche tous les liens disponibles avec des boutons."
    )
    async def randeck(self, ctx: commands.Context):
        try:
            data = load_data()
            decks = []

            # Construire une liste de (saison, personnage, niveau, dict liens)
            for saison, persos in data.items():
                for duelliste, infos in persos.items():
                    deck_data = infos.get("deck", {})
                    if not isinstance(deck_data, dict):
                        continue
                    for niveau, liens in deck_data.items():
                        if isinstance(liens, dict) and liens:
                            decks.append((saison, duelliste, niveau, liens))

            if not decks:
                return await safe_send(ctx, "❌ Aucun deck n'est disponible.")

            # Tirage aléatoire
            saison, duelliste, niveau, liens_dict = random.choice(decks)

            # ─ Embed stylé ─
            embed = discord.Embed(
                title="🎲 Deck Aléatoire Tiré !",
                color=discord.Color.random()
            )
            embed.add_field(
                name="👤 Duelliste",
                value=f"**{duelliste}** *(Saison : {saison})*",
                inline=False
            )
            embed.add_field(
                name="🎚️ Niveau",
                value=niveau,
                inline=False
            )

            # ── Création des boutons pour tous les liens ──
            view = discord.ui.View()
            for nom, url in liens_dict.items():
                view.add_item(discord.ui.Button(label=nom, url=url))

            embed.set_footer(
                text=f"Tiré par {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )

            await safe_send(ctx.channel, embed=embed, view=view)

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
