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
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

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
        description="Affiche toutes les informations du tournoi VAACT."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_vaact(self, interaction: discord.Interaction):
        """Commande slash d'information VAACT."""

        embed = self._build_embed()
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="vaact",
        aliases = ["info"],
        help="Présentation du tournoi animé Yu-Gi-Oh! (VAACT).",
        description="Affiche toutes les informations du tournoi VAACT."
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_vaact(self, ctx: commands.Context):
        """Commande préfixe d'information VAACT."""

        embed = self._build_embed()
        await safe_send(ctx.channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Embed builder
    # ────────────────────────────────────────────────────────────────────────────
    def _build_embed(self) -> discord.Embed:
        """Construit l'embed VAACT."""

        embed = discord.Embed(
            title="🎴 **Le VAACT (Tournoi animé Yu-Gi-Oh!)**",
            description=(
                "**Le VAACT c'est quoi ?**\n"
                "Marre de la méta ? De jouer les mêmes matchs miroirs ?\n"
                "De ne pas pouvoir jouer car les cartes coûtent trop cher ? 😭\n"
                "✨ Découvrez le **tournoi animé Yu-Gi-Oh! VAACT**"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🃏 Concept",
            value=(
                "● Jouez avec les **Decks de vos personnages préférés**\n"
                "issus des **6 séries Yu-Gi-Oh!**\n"
                "● Les decks sont **pré-construits** et prétés le temps du tournoi donc pas de panique !\n"
                "Les decks sont fidèles à l’animé pour une expérience unique 👌"
            ),
            inline=False
        )

        embed.add_field(
            name="✍️ Participation",
            value=(
                "✅ La Pré-inscription se fait sur Instagram en DM avec le Deck choisi\n"
                "📋 Liste des Decks disponibles :\n"
                "https://docs.google.com/spreadsheets/d/1ifAWeG16Q-wULckgOVOBpsjgYJ25k-9gtQYtivYBCtI/edit#gid=0\n\n"
                "❌ Pas besoin de cartes\n"
                "💸 **Entrée à prix libre** (mais 5€ au moins ce serait sympa)"
            ),
            inline=False
        )

        embed.add_field(
            name="👥 Places",
            value="Jusqu’à **16 joueurs** — premier arrivé, premier servi 🚤",
            inline=False
        )

        embed.add_field(
            name="📍 Lieu & horaires",
            value=(
                "**Ludotrotteur Nantes**\n"
                "11 rue du Printemps, Orvault\n\n"
                "🚌 Tram L2, Bus C2, etc.\n"
                "🗓️ **Tous les 3 vendredis à 19h**\n"
                "⏰ Pré-inscriptions : **1 semaine avant**"
            ),
            inline=False
        )

        embed.add_field(
            name="🏆 Récompenses",
            value=(
                "📅 Saison de **6 mois** avec système de points\n\n"
                "🥇 Vainqueur de la saison :\n"
                "• Une **display** 🎴\n"
                "• OU un **playmat / sleeves custom** 😌\n\n"
                "🎁 **Boosters** à gagner à chaque tournoi\n"
                "(selon les inscriptions 💰)"
            ),
            inline=False
        )

        embed.set_footer(
            text="Duellistes de tous bords, c’est l’heure du Duel ! ⚡"
        )

        return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Vaact(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
