# ────────────────────────────────────────────────────────────────────────────────
# 📌 sync.py — Commande simple /sync et !sync
# Objectif : Synchroniser les commandes slash avec Discord (serveur ou global)
# Catégorie : Admin
# Accès : Owner uniquement
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Sync(commands.Cog):
    """
    Commande /sync et !sync — Synchronise les commandes slash (serveur ou global)
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="sync",
        description="(Admin) Synchronise les commandes slash (serveur ou global)."
    )
    @app_commands.describe(scope="Tape 'global' pour synchroniser toutes les guildes.")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.user.id))
    async def slash_sync(self, interaction: discord.Interaction, scope: str = None):
        """Commande slash pour synchroniser les commandes (guild ou global)."""
        try:
            if not await self.bot.is_owner(interaction.user):
                return await safe_respond(interaction, "⛔ Cette commande est réservée au propriétaire du bot.", ephemeral=True)

            if scope and scope.lower() == "global":
                synced = await self.bot.tree.sync()
                msg = f"🌍 **{len(synced)} commandes globales synchronisées avec Discord !**"
            else:
                if interaction.guild:
                    self.bot.tree.copy_global_to(guild=interaction.guild)
                    synced = await self.bot.tree.sync(guild=interaction.guild)
                    msg = f"🏠 **{len(synced)} commandes synchronisées uniquement pour ce serveur !**"
                else:
                    msg = "❌ Impossible de synchroniser localement car cette commande n'a pas été exécutée dans un serveur."

            await safe_respond(interaction, msg, ephemeral=True)

        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /sync] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue lors de la synchronisation.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="sync", help="(Admin) Synchronise les commandes slash (serveur ou global).")
    @commands.is_owner()
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_sync(self, ctx: commands.Context, scope: str = None):
        """Commande préfixe pour synchroniser les commandes (guild ou global)."""
        try:
            if scope and scope.lower() == "global":
                synced = await ctx.bot.tree.sync()
                msg = f"🌍 **{len(synced)} commandes globales synchronisées avec Discord !**"
            else:
                if ctx.guild:
                    self.bot.tree.copy_global_to(guild=ctx.guild)
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                    msg = f"🏠 **{len(synced)} commandes synchronisées uniquement pour ce serveur !**"
                else:
                    msg = "❌ Impossible de synchroniser localement car cette commande n'a pas été exécutée dans un serveur."

            await safe_send(ctx.channel, msg)

        except commands.CommandOnCooldown as e:
            await safe_send(ctx.channel, f"⏳ Attends encore {e.retry_after:.1f}s.")
        except Exception as e:
            print(f"[ERREUR !sync] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors de la synchronisation.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Sync(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
