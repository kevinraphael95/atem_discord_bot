# ────────────────────────────────────────────────────────────────────────────────
# 📌 ping.py — Commande interactive !ping
# Objectif : Vérifie la latence du bot
# Catégorie : 🧱 Général
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands

from utils.discord_utils import safe_send  # ✅ Sécurise l'envoi (anti-429)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Ping(commands.Cog):
    """
    Commande !ping — Vérifie la latence du bot.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="ping",
        aliases=["pong", "latence"],
        help="Affiche la latence actuelle du bot.",
        description="Affiche la latence actuelle du bot en millisecondes."
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def ping(self, ctx: commands.Context):
        """Répond avec la latence actuelle du bot."""
        try:
            latence = round(self.bot.latency * 1000)
            await safe_send(ctx, f"🏓 Pong ! Latence : **{latence} ms**")
        except Exception as e:
            print("[ERREUR ping]", e)
            await safe_send(ctx, "❌ Une erreur est survenue lors de l'exécution de la commande.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Ping(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
