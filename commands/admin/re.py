# ────────────────────────────────────────────────────────────────────────────────
# 📌 redemarrage_command.py — Commande simple /re et !re
# Objectif : Prévenir les membres et déclencher un redeploy Render via webhook
# Catégorie : ⚙️ Admin
# Accès : Administrateur
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond
import aiohttp
import os
import asyncio

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class RedemarrageCommand(commands.Cog):
    """
    Commande /re et !re — Préviens les membres, déclenche un redeploy sur Render et notifie quand le bot est redeployé.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.render_webhook = os.getenv("RENDER_REDEPLOY_WEBHOOK")  # URL du webhook Render
        self.render_service_api = os.getenv("RENDER_SERVICE_API")    # API Render pour vérifier l'état du service

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="re",
        description="(Admin) Préviens les membres et redémarre le bot via Render."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_re(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            await self._trigger_restart(interaction.channel)
        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /re] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="re",
        help="(Admin) Préviens les membres et redémarre le bot via Render.",
        description="Commande préfixe pour annoncer et déclencher le redeploy."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix_re(self, ctx: commands.Context):
        await self._trigger_restart(ctx.channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne de redeploy
    # ────────────────────────────────────────────────────────────────────────────
    async def _trigger_restart(self, channel: discord.abc.Messageable):
        """Annonce le redémarrage, déclenche le redeploy Render et confirme quand le bot est redeployé."""
        try:
            # 1️⃣ Préviens les membres
            embed = discord.Embed(
                title="🔃 Redémarrage",
                description="Le bot va redémarrer sous peu...",
                color=discord.Color.red()
            )
            await safe_send(channel, embed=embed)

            # 2️⃣ Déclenche le redeploy via webhook
            if not self.render_webhook:
                await safe_send(channel, "⚠️ Webhook Render non configuré.")
                return

            async with aiohttp.ClientSession() as session:
                async with session.post(self.render_webhook) as resp:
                    if resp.status in (200, 201):
                        await safe_send(channel, "✅ Redeploy demandé avec succès sur Render !")
                    else:
                        await safe_send(channel, f"❌ Échec du redeploy. Code HTTP : {resp.status}")
                        return

                # 3️⃣ Attente que le service soit redeployé
                if not self.render_service_api:
                    await safe_send(channel, "⚠️ API Render pour le service non configurée. Impossible de vérifier l'état du redeploy.")
                    return

                # Polling du service
                max_checks = 100
                for i in range(max_checks):
                    async with session.get(self.render_service_api) as status_resp:
                        if status_resp.status == 200:
                            await safe_send(channel, "🎉 Le bot a été redeployé et est de nouveau en ligne !")
                            return
                    await asyncio.sleep(5)  # attendre 5s avant le prochain check

                await safe_send(channel, "⚠️ Timeout : le bot ne semble pas être redeployé dans les temps attendu.")

        except Exception as e:
            print(f"[REDEPLOY] Erreur : {e}")
            await safe_send(channel, f"❌ Une erreur est survenue lors du redeploy : `{e}`")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RedemarrageCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
