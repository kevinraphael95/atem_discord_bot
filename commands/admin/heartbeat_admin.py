# ────────────────────────────────────────────────────────────────────────────────
# 📌 heartbeat_admin.py — Commande !heartbeat <pause|resume|status|set|unset>
# Objectif : Gérer tout le heartbeat via une seule commande (pause, relance, statut, salon)
# Catégorie : Heartbeat
# Accès : Modérateur (permission admin requise)
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from utils.discord_utils import safe_send  # Fonctions safe pour envoyer messages sans risquer erreurs Discord

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class HeartbeatAdmin(commands.Cog):
    """
    Commande !heartbeat — Gère le heartbeat automatique (pause, relance, statut, salon)
    """
    # Initialisation du cog avec accès au bot et à Supabase
    def __init__(self, bot: commands.Bot):
        self.bot = bot  # Stocke la référence du bot
        self.supabase = bot.supabase  # Accès à Supabase pour stocker et lire les settings

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="heartbeat",  # Nom de la commande préfixe
        aliases=["hb"],  # Alias pour simplifier
        help="(Admin) Gère le heartbeat : pause, resume, status, set, unset.",  # Description courte
        description="Gère le heartbeat automatique (pause, relance, statut, salon)."  # Description détaillée
    )
    @commands.has_permissions(administrator=True)  # Vérifie que l'utilisateur est admin
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)  # Cooldown 5s par utilisateur
    async def heartbeat(self, ctx: commands.Context, action: str = None, channel: discord.TextChannel = None):
        """Commande préfixe pour gérer le heartbeat"""

        # Si aucune action n'est donnée, affiche l'aide rapide
        if not action:
            await safe_send(ctx, "❓ Utilisation : `!heartbeat pause|resume|status|set <#salon>|unset`")
            return

        # Normalise l'action en minuscule
        action = action.lower()

        # ───────────── Pause / Resume ─────────────
        # Pause le heartbeat
        if action in ["pause", "p"]:
            # Met à jour Supabase pour indiquer que le heartbeat est en pause
            self.supabase.table("bot_settings").upsert({"key": "heartbeat_paused", "value": "true"}).execute()
            await safe_send(ctx, "⏸️ Heartbeat mis en pause.")

        # Relance le heartbeat
        elif action in ["resume", "r"]:
            # Met à jour Supabase pour indiquer que le heartbeat est actif
            self.supabase.table("bot_settings").upsert({"key": "heartbeat_paused", "value": "false"}).execute()
            await safe_send(ctx, "▶️ Heartbeat relancé.")

        # ───────────── Status ─────────────
        elif action in ["status", "stat", "s"]:
            # Récupère le statut actuel du heartbeat depuis Supabase
            res = self.supabase.table("bot_settings").select("value").eq("key", "heartbeat_paused").execute()
            # Vérifie si le heartbeat est en pause
            paused = res.data and res.data[0]["value"].lower() == "true"
            # Prépare le message en fonction du statut
            status_msg = "🔴 Le heartbeat est **en pause**." if paused else "🟢 Le heartbeat est **actif**."
            await safe_send(ctx, status_msg)

        # ───────────── Set / Unset salon ─────────────
        elif action == "set":
            # Vérifie qu'un salon est mentionné
            if not channel:
                await safe_send(ctx, "❌ Tu dois mentionner un salon. Exemple : `!heartbeat set #général`")
                return
            # Met à jour Supabase avec l'ID du salon
            self.supabase.table("bot_settings").upsert({"key": "heartbeat_channel_id", "value": str(channel.id)}).execute()
            # Si le cog HeartbeatTask est chargé, met à jour son salon directement
            heartbeat_cog = self.bot.get_cog("HeartbeatTask")
            if heartbeat_cog:
                heartbeat_cog.heartbeat_channel_id = channel.id
            await safe_send(ctx, f"✅ Salon heartbeat défini : {channel.mention}")

        elif action == "unset":
            # Supprime l'ID du salon dans Supabase
            self.supabase.table("bot_settings").upsert({"key": "heartbeat_channel_id", "value": ""}).execute()
            # Si le cog HeartbeatTask est chargé, supprime la référence du salon
            heartbeat_cog = self.bot.get_cog("HeartbeatTask")
            if heartbeat_cog:
                heartbeat_cog.heartbeat_channel_id = None
            await safe_send(ctx, "🗑️ Salon heartbeat supprimé.")

        # ───────────── Action inconnue ─────────────
        else:
            # Message d'erreur si l'action n'est pas reconnue
            await safe_send(ctx, "❌ Action inconnue. Utilise `pause`, `resume`, `status`, `set`, ou `unset`")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = HeartbeatAdmin(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
                            
