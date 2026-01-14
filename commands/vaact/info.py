# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact.py — Commande interactive !vaact
# Objectif : Présentation du tournoi animé Yu-Gi-Oh! VAACT
# Catégorie : Yu-Gi-Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Vaact(commands.Cog):
    """
    Commande !vaact — Informations sur le tournoi animé Yu-Gi-Oh!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="vaact",
        help="Présentation du tournoi animé Yu-Gi-Oh! (VAACT).",
        description="Affiche toutes les informations du tournoi VAACT."
    )
    async def vaact(self, ctx: commands.Context):
        """Commande principale d'information VAACT."""

        embed = discord.Embed(
            title="🎴 **Le VAACT (Tournoi animé Yu-Gi-Oh!)**",
            description=(
                "**Marre de la méta ?**\n"
                "De jouer les mêmes matchs miroirs ?\n"
                "De ne pas pouvoir jouer car les cartes coûtent trop cher ? 😭\n\n"
                "✨ Je vous présente mon projet de **tournoi animé Yu-Gi-Oh!**"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🃏 Concept",
            value=(
                "● Jouez avec les **Decks de vos personnages préférés**\n"
                "issus des **6 séries Yu-Gi-Oh!**\n"
                "● Pas de Deck animé ? Aucun souci :\n"
                "les Decks sont **pré-construits** par mes soins,\n"
                "fidèles à l’animé pour une expérience unique 👌"
            ),
            inline=False
        )

        embed.add_field(
            name="✍️ Participation",
            value=(
                "✅ Pré-inscription par **MP** avec le Deck choisi\n"
                "📋 Liste des Decks disponibles :\n"
                "https://docs.google.com/spreadsheets/d/1ifAWeG16Q-wULckgOVOBpsjgYJ25k-9gtQYtivYBCtI/edit#gid=0\n\n"
                "❌ Pas besoin de cartes\n"
                "💸 **Entrée à prix libre**"
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

        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Vaact(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Yu-Gi-Oh"
    await bot.add_cog(cog)
