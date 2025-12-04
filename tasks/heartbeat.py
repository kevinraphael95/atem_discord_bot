# ────────────────────────────────────────────────────────────────────────────────
# 📌 heartbeat.py — Task automatique d'envoi du heartbeat toutes les 5 minutes
# Objectif : Garder le bot alive et détecter les erreurs de self-ping
# Catégorie : Général
# Accès : Interne (aucune commande ici)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
from utils.discord_utils import safe_send  # <-- Import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class HeartbeatTask(commands.Cog):
    """
    Task qui envoie un message toutes les 5 minutes dans un salon configuré.
    Réagit aussi aux erreurs de keep_alive.py (flag ping_failed).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase = bot.supabase
        self.heartbeat_channel_id = None
        self.heartbeat_task.start()

    def cog_unload(self):
        self.heartbeat_task.cancel()

    @tasks.loop(minutes=5)
    async def heartbeat_task(self):
        # 🔒 Vérifie si le heartbeat est en pause
        try:
            pause_res = self.supabase.table("bot_settings").select("value").eq("key", "heartbeat_paused").execute()
            if pause_res.data and pause_res.data[0]["value"].lower() == "true":
                print("[Heartbeat] Pausé — aucune action envoyée.")
                return
        except Exception as e:
            print(f"[Heartbeat] Erreur lecture heartbeat_paused : {e}")

        # 🔍 Vérifie le salon configuré
        if not self.heartbeat_channel_id:
            await self.load_heartbeat_channel()

        # ─────────────────────────────────────────────
        # ⚠️ Vérifie si le self-ping a échoué
        # ─────────────────────────────────────────────
        try:
            ping_error = self.supabase.table("bot_settings").select("value").eq("key", "ping_failed").execute()
            if ping_error.data and ping_error.data[0]["value"] == "true":
                channel = self.bot.get_channel(self.heartbeat_channel_id)
                if channel:
                    await safe_send(channel, "⚠️ **Self-ping Render KO !** Le bot a peut-être été réveillé.")
                    print("[Heartbeat] Alerte envoyée suite à un ping_failed.")

                    # Reset du flag
                    self.supabase.table("bot_settings").update({"value": "false"}).eq("key", "ping_failed").execute()
        except Exception as e:
            print(f"[Heartbeat] Erreur lecture ping_failed : {e}")

        # ─────────────────────────────────────────────
        # 💓 Envoi du heartbeat normal
        # ─────────────────────────────────────────────
        if self.heartbeat_channel_id:
            channel = self.bot.get_channel(self.heartbeat_channel_id)
            if channel:
                try:
                    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    await safe_send(channel, f"💓 Boom boom ! ({now})")
                except Exception as e:
                    print(f"[Heartbeat] Erreur en envoyant le message : {e}")
            else:
                print("[Heartbeat] Salon non trouvé — reconfigurer heartbeat_channel_id.")

    @heartbeat_task.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()
        await self.load_heartbeat_channel()

    async def load_heartbeat_channel(self):
        try:
            resp = self.supabase.table("bot_settings").select("value").eq("key", "heartbeat_channel_id").execute()
            if resp.data and len(resp.data) > 0:
                val = resp.data[0]["value"]
                if val.isdigit():
                    self.heartbeat_channel_id = int(val)
                    print(f"[Heartbeat] Salon heartbeat chargé : {self.heartbeat_channel_id}")
                else:
                    print("[Heartbeat] Valeur heartbeat_channel_id invalide.")
            else:
                print("[Heartbeat] Aucun salon heartbeat configuré.")
        except Exception as e:
            print(f"[Heartbeat] Erreur chargement Supabase : {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(HeartbeatTask(bot))
