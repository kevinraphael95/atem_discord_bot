# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact.py — Commande simple /vaact et !vaact
# Objectif : Présentation du tournoi animé Yu-Gi-Oh! VAACT
# Catégorie : VAACT
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Vaact(commands.Cog):
    """
    Commande /vaact et !vaact — Informations sur le tournoi animé Yu-Gi-Oh!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="vaact",
        description="Présentation rapide du tournoi animé Yu-Gi-Oh! VAACT."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_vaact(self, interaction: discord.Interaction):
        embed = self._build_embed()
        view = VaactLinksView()
        await safe_respond(interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="vaact",
        aliases=["info"],
        help="Présentation rapide du tournoi animé Yu-Gi-Oh! VAACT."
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_vaact(self, ctx: commands.Context):
        embed = self._build_embed()
        view = VaactLinksView()
        await safe_send(ctx.channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Embed builder
    # ────────────────────────────────────────────────────────────────────────────
    def _build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎴 Le VAACT — Tournoi animé Yu-Gi-Oh!",
            description=(
                "**Marre de la méta et des cartes hors de prix ?** 😭\n"
                "Le **VAACT** est un tournoi Yu-Gi-Oh! basé sur l’animé,\n"
                "avec des **Decks de personnages pré-construits** ✨"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🃏 Concept",
            value=(
                "• Decks des **personnages de l’animé**\n"
                "• **Decks prêtés**, aucun achat requis\n"
                "• Fun, accessible et fidèle à l’animé 👌"
            ),
            inline=False
        )

        embed.add_field(
            name="📍 Infos pratiques",
            value=(
                "👥 **16 joueurs max**\n"
                "🗓️ Tous les **3 vendredis à 19h**\n"
                "📌 Ludotrotteur Nantes\n"
                "💸 **Entrée à prix libre**"
            ),
            inline=False
        )

        embed.set_footer(
            text="Pré-inscription en DM Instagram — premier arrivé, premier servi ⚡"
        )

        return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🔗 View — Boutons liens
# ────────────────────────────────────────────────────────────────────────────────
class VaactLinksView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            Button(
                label="📋 Liste des Decks",
                style=discord.ButtonStyle.link,
                url="https://docs.google.com/spreadsheets/d/1ifAWeG16Q-wULckgOVOBpsjgYJ25k-9gtQYtivYBCtI/edit#gid=0"
            )
        )

        self.add_item(
            Button(
                label="📸 Instagram VAACT",
                style=discord.ButtonStyle.link,
                url="https://www.instagram.com/vaactyugioh"
            )
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Vaact(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
