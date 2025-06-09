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
        help="Affiche les nouveautés et derniers changements du bot."
    )
    async def info(self, ctx: commands.Context):
        """Commande principale qui envoie un embed avec les nouveautés."""
        prefix = ctx.prefix  # Récupère le préfixe dynamique utilisé par le bot

        changelog_lines = [
            f"• La commande {prefix}illustration devient multijoueur, vous pouvez répondre quand les autres font la commande!",
            f"• La commande {prefix}illustration a maintenant aussi un leaderboard, donné automatiquement quand quelqu'un donne une réponse à la commande.",
            f"• Ajout de la commande {prefix}info",
            f"• La commande {prefix}tournoi permet de voir la date du prochain tournoi VAACT et mettre un rappel en MP trois jours avant."
        ]

        embed = discord.Embed(
            title="🛠️ Nouveautés et derniers changements",
            color=discord.Color.blue()
        )
        embed.description = "\n".join(changelog_lines)
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
