# ────────────────────────────────────────────────────────────────────────────────
# 📌 redemarrage_command.py — Commande interactive !re (redémarrage)
# Objectif : Prévenir les membres du redémarrage du bot
# Catégorie : ⚙️ Admin
# Accès : Modérateur (Administrateur)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class RedemarrageCommand(commands.Cog):
    """
    Commande !re — Préviens les membres du redémarrage du bot.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="re",
        help="(Admin) Préviens les membres du redémarrage du bot.",
        description="Commande réservée aux administrateurs pour annoncer un redémarrage imminent."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def re(self, ctx: commands.Context):
        """Envoie un message embed pour signaler le redémarrage du bot."""
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass  # Ignore si pas la permission de supprimer le message

        embed = discord.Embed(
            title="🔃 Redémarrage",
            description="Le bot va redémarrer sous peu.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RedemarrageCommand(bot)
    for command in cog.get_commands():
        command.category = "Général"
    await bot.add_cog(cog)
