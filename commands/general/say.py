# ────────────────────────────────────────────────────────────────────────────────
# 📌 say.py — Commande !say
# Objectif : Fait répéter un message par le bot et supprime l’original
# Catégorie : Général
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from utils.discord_utils import safe_send  # ✅ Utilisation des safe_

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class SayCommand(commands.Cog):
    """
    Commande !say — Fait répéter un message par le bot
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="say",
        help="Fait répéter un message par le bot et supprime le message d'origine.",
        description="Le bot répète le message donné. Le message original est supprimé s’il est supprimable."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)  # ⏱️ Anti-spam 3s
    async def say(self, ctx: commands.Context, *, message: str):
        """Commande principale !say"""
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass  # 🧽 Ignore si on ne peut pas supprimer le message original

        try:
            await safe_send(ctx.channel, message)
        except Exception as e:
            print(f"[ERREUR !say] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue en répétant le message.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = SayCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
