# ────────────────────────────────────────────────────────────────────────────────
# 📌 mtgtuto.py — Commande /mtgtuto et !mtgtuto
# Objectif : Tutoriel interactif pour apprendre à jouer à Magic: The Gathering
# Catégorie : MagicTCG
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 📘 Pages du tutoriel
# ────────────────────────────────────────────────────────────────────────────────
MTG_TUTORIAL_PAGES = [
    {
        "title": "🧙 Magic: The Gathering — Introduction",
        "description": (
            "**Magic: The Gathering (MTG)** est le tout premier jeu de cartes à collectionner.\n\n"
            "Chaque joueur incarne un **Planeswalker**, un puissant mage capable d’invoquer "
            "créatures, sorts et artefacts.\n\n"
            "🎯 **Objectif principal** : réduire les **points de vie** de l’adversaire à **0**."
        )
    },
    {
        "title": "🃏 Types de cartes",
        "description": (
            "Les principaux types de cartes :\n\n"
            "🐉 **Créature** — Attaque et bloque\n"
            "✨ **Éphémère** — Jouable à tout moment\n"
            "📜 **Rituel** — Jouable pendant ton tour\n"
            "🧿 **Enchantement** — Effet durable\n"
            "⚙️ **Artefact** — Objet magique\n"
            "🌍 **Terrain** — Produit du mana\n\n"
            "Une carte peut avoir **plusieurs types**."
        )
    },
    {
        "title": "🌍 Terrains & Mana",
        "description": (
            "Le **mana** est la ressource du jeu.\n\n"
            "Chaque **terrain** produit du mana :\n"
            "⚪ Plaine → Blanc\n"
            "🔵 Île → Bleu\n"
            "⚫ Marais → Noir\n"
            "🔴 Montagne → Rouge\n"
            "🟢 Forêt → Vert\n\n"
            "🔹 Tu peux poser **1 terrain par tour**."
        )
    },
    {
        "title": "⏱️ Déroulement d’un tour",
        "description": (
            "Un tour se déroule en **phases** :\n\n"
            "1️⃣ Dégagement\n"
            "2️⃣ Entretien\n"
            "3️⃣ Pioche\n"
            "4️⃣ Phase principale\n"
            "5️⃣ Combat\n"
            "6️⃣ Seconde phase principale\n"
            "7️⃣ Fin du tour\n\n"
            "👉 Certains sorts peuvent être joués **pendant le tour adverse**."
        )
    },
    {
        "title": "⚔️ Le combat",
        "description": (
            "Le combat se déroule ainsi :\n\n"
            "🗡️ Déclaration des attaquants\n"
            "🛡️ Déclaration des bloqueurs\n"
            "💥 Attribution des dégâts\n\n"
            "⚠️ Une créature engagée ne peut PAS bloquer.\n"
            "⚠️ Les blessures restent jusqu’à la fin du tour."
        )
    },
    {
        "title": "🏆 Gagner la partie",
        "description": (
            "Tu peux gagner de plusieurs façons :\n\n"
            "❤️ Réduire l’adversaire à **0 PV**\n"
            "☠️ Empoisonnement (10 marqueurs)\n"
            "📉 Meule (plus de carte à piocher)\n"
            "📜 Conditions spéciales de cartes\n\n"
            "✨ Magic est un jeu **stratégique et infini**."
        )
    }
]

# ────────────────────────────────────────────────────────────────────────────────
# 🧭 Vue avec boutons
# ────────────────────────────────────────────────────────────────────────────────
class MTGTutorialView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.index = 0

    def get_embed(self) -> discord.Embed:
        page = MTG_TUTORIAL_PAGES[self.index]
        embed = discord.Embed(
            title=page["title"],
            description=page["description"],
            color=discord.Color.red()
        )
        embed.set_footer(
            text=f"Page {self.index + 1}/{len(MTG_TUTORIAL_PAGES)} • Tutoriel Magic"
        )
        return embed

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(MTG_TUTORIAL_PAGES) - 1:
            self.index += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MTGTuto(commands.Cog):
    """Commande /mtgtuto et !mtgtuto — Tutoriel Magic"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="mtgtuto",
        description="Apprendre à jouer à Magic: The Gathering"
    )
    async def slash_mtgtuto(self, interaction: discord.Interaction):
        view = MTGTutorialView()
        await safe_respond(interaction, embed=view.get_embed(), view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mtgtuto", help="Apprendre à jouer à Magic: The Gathering")
    async def prefix_mtgtuto(self, ctx: commands.Context):
        view = MTGTutorialView()
        await safe_send(ctx.channel, embed=view.get_embed(), view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MTGTuto(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "MagicTCG"
    await bot.add_cog(cog)
