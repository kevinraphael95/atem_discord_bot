# ────────────────────────────────────────────────────────────────────────────────
# 📌 info.py — Commande !info
# Objectif : Afficher les nouveautés / derniers changements du bot dans un embed simple
# Catégorie : Général
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class InfoCog(commands.Cog):
    """
    Commande !info — Affiche les nouveautés et derniers changements du bot.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="info",
        help="Présente le bot et ce qu'il fait."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)  # 🧊 Anti-spam : 1 appel / 3s / utilisateur
    async def info(self, ctx: commands.Context):
        """Commande principale qui envoie un embed avec les nouveautés."""
        prefix = ctx.prefix  # Récupère le préfixe dynamique utilisé par le bot

        embed = discord.Embed(
            title="Présentation du bot",
            color=discord.Color.blue()
        )


        # Section Yugioh
        embed.add_field(
            name="🃏 Yu-Gi-Oh!",
            value=(
                "\n"
                "**• Question :** Devinez la carte avec sa description.\n"
                "( Y'a aussi TestQuestion, une tentative d'ammélioration de la commande question, test. )\n"
                "**• Illustration :** Devinez la carte avec son illustration.\n"
                "**• Carte :** Chercher les infos d'une carte avec son nom français ou anglais."
            ),
            inline=False
        )

        # Section VAACT
        embed.add_field(
            name="🎮 VAACT",
            value=(
                "**• Tournoi :** Regardez si un tournoi VAACT est prévu et si oui sa date.\n"
                "**• Deck :** Regardez les decks custom du tournoi version animé/manga (y'aura des astuces avec peut-être un jour)"
            ),
            inline=False
        )

        # Footer
        embed.set_footer(text="Merci d'utiliser le bot !")

        await ctx.send(embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = InfoCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
