# ────────────────────────────────────────────────────────────────────────────────
# 📌 lortuto.py — Commande /lortuto et !lortuto
# Objectif : Tutoriel interactif pour apprendre à jouer à Disney Lorcana
# Catégorie : LorcanaTCG
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
LORCANA_TUTORIAL_PAGES = [
    {
        "title": "🎴 Disney Lorcana — Introduction",
        "description": (
            "**Disney Lorcana** est un jeu de cartes à collectionner.\n\n"
            "Tu incarnes un **Illumineur**, capable d’invoquer des personnages Disney "
            "sous forme d’**encres magiques** appelées *Glimmers*.\n\n"
            "🎯 **Objectif** : être le premier joueur à atteindre **20 points de Lore**."
        )
    },
    {
        "title": "🃏 Types de cartes",
        "description": (
            "Il existe plusieurs types de cartes :\n\n"
            "👤 **Personnage** — Peut chercher du Lore et défier\n"
            "✨ **Action** — Effet immédiat\n"
            "🏰 **Objet** — Effet permanent\n"
            "📜 **Chanson** — Action spéciale, souvent jouable par des personnages\n\n"
            "Chaque carte a un **coût**, une **couleur**, et parfois des **capacités**."
        )
    },
    {
        "title": "💧 L’Encre & le coût",
        "description": (
            "L’**Encre** est la ressource principale du jeu.\n\n"
            "🔹 Une fois par tour, tu peux **placer 1 carte en Encre** "
            "(si elle est *Inkable*).\n\n"
            "🔹 Jouer une carte consomme de l’Encre.\n\n"
            "⚠️ Les cartes **Non-Inkable** ne peuvent PAS être mises en Encre."
        )
    },
    {
        "title": "⚔️ Déroulement d’un tour",
        "description": (
            "Un tour se déroule ainsi :\n\n"
            "1️⃣ Redresser toutes tes cartes\n"
            "2️⃣ Piocher 1 carte\n"
            "3️⃣ Mettre 1 carte en Encre (optionnel)\n"
            "4️⃣ Jouer des cartes\n"
            "5️⃣ Envoyer des personnages en quête (Lore)\n"
            "6️⃣ Défier des personnages adverses\n\n"
            "➡️ Puis tu termines ton tour."
        )
    },
    {
        "title": "🏆 Gagner la partie",
        "description": (
            "Tu gagnes dès que tu atteins **20 Lore** 🎉\n\n"
            "💡 Astuces :\n"
            "• Protéger tes personnages en quête\n"
            "• Bien gérer ton Encre\n"
            "• Savoir quand attaquer ou temporiser\n\n"
            "✨ L’équilibre est la clé !"
        )
    }
]

# ────────────────────────────────────────────────────────────────────────────────
# 🧭 Vue avec boutons
# ────────────────────────────────────────────────────────────────────────────────
class LorcanaTutorialView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.index = 0

    def get_embed(self) -> discord.Embed:
        page = LORCANA_TUTORIAL_PAGES[self.index]
        embed = discord.Embed(
            title=page["title"],
            description=page["description"],
            color=discord.Color.purple()
        )
        embed.set_footer(
            text=f"Page {self.index + 1}/{len(LORCANA_TUTORIAL_PAGES)} • Tutoriel Lorcana"
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
        if self.index < len(LORCANA_TUTORIAL_PAGES) - 1:
            self.index += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class LorTuto(commands.Cog):
    """Commande /lortuto et !lortuto — Tutoriel Lorcana"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="lortuto",
        description="Apprendre à jouer à Disney Lorcana (tutoriel interactif)"
    )
    async def slash_lortuto(self, interaction: discord.Interaction):
        view = LorcanaTutorialView()
        await safe_respond(interaction, embed=view.get_embed(), view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="lortuto", help="Apprendre à jouer à Disney Lorcana (tutoriel interactif)")
    async def prefix_lortuto(self, ctx: commands.Context):
        view = LorcanaTutorialView()
        await safe_send(ctx.channel, embed=view.get_embed(), view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = LorTuto(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "LorcanaTCG"
    await bot.add_cog(cog)
