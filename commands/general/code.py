# ────────────────────────────────────────────────────────────────────────────────
# 📌 code.py — Commande interactive !code
# Objectif : Afficher le lien vers le dépôt GitHub du bot
# Catégorie : 🧠 Général
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — Commande !code
# ────────────────────────────────────────────────────────────────────────────────
class Code(commands.Cog):
    """
    💻 Commande !code — Affiche le lien vers le dépôt GitHub du bot
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="code",
        help="💻 Affiche le lien vers le dépôt GitHub du bot.",
        description="Envoie un embed avec le lien du dépôt GitHub."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)  # 🧊 Anti-spam : 1 appel / 3s / utilisateur
    async def code(self, ctx: commands.Context):
        """Commande principale !code"""
        try:
            embed = discord.Embed(
                title="💻 Code source du bot",
                description="[📂 Voir le dépôt GitHub](https://github.com/kevinraphael95/atem_discord_bot)",
                color=discord.Color.blurple()
            )
            embed.set_footer(text="✨ Open-source, baby ! | Projet Yu Gi Oooooh !")
            await ctx.send(embed=embed)
        except Exception as e:
            print("[ERREUR - COMMANDE !code]", e)
            await ctx.send("🚨 Une erreur est survenue lors de l’envoi du lien vers le code source.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Code(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
