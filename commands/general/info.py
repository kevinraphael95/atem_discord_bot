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
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)  # 🧊 Anti-spam : 1 appel / 3s / utilisateur
    async def info(self, ctx: commands.Context):
        """Commande principale qui envoie un embed avec les nouveautés."""
        prefix = ctx.prefix  # Récupère le préfixe dynamique utilisé par le bot

        changelog_lines = [
            f"• Commande $question :\n"
            f"- Commande maintenant multijoueur\n"
            f"- De meilleures propositions de noms quand la carte n'a aucun archétype"
        ]

        embed = discord.Embed(
            title="🛠️ Derniers changements",
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
