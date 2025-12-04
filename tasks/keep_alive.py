# ────────────────────────────────────────────────────────────────────────────────
# 📌 keep_alive.py — Serveur Flask + self-ping amélioré
# Objectif : Maintenir le bot en ligne sur Render / Replit + signaler les erreurs
# Catégorie : Task
# Accès : Interne
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
import asyncio
from threading import Thread
from flask import Flask
import aiohttp
from utils.supabase_client import supabase_client

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Serveur Flask
# ────────────────────────────────────────────────────────────────────────────────
app = Flask("")

@app.route("/")
def home():
    return "Bot en ligne ! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ────────────────────────────────────────────────────────────────────────────────
# 🔄 Boucle de self-ping améliorée
# ────────────────────────────────────────────────────────────────────────────────
async def ping_loop():

    ping_url = os.environ.get("PING_URL")
    if not ping_url:
        print("[KEEP_ALIVE] ⚠️ PING_URL manquant → self-ping désactivé.")
        return

    async with aiohttp.ClientSession() as session:
        while True:
            ping_failed_value = "false"  # Valeur par défaut

            try:
                async with session.get(ping_url) as resp:
                    print(f"[KEEP_ALIVE] Ping → {resp.status}")
                    if resp.status != 200:
                        ping_failed_value = "true"
            except Exception as e:
                print(f"[KEEP_ALIVE] Erreur ping : {e}")
                ping_failed_value = "true"

            # ─────────────────────────────────────────────
            # ⚠️ Met à jour Supabase
            # ─────────────────────────────────────────────
            try:
                # Vérifie si la clé existe
                res = supabase_client.table("bot_settings").select("value").eq("key", "ping_failed").execute()
                if res.data:
                    supabase_client.table("bot_settings").update({"value": ping_failed_value}).eq("key", "ping_failed").execute()
                else:
                    supabase_client.table("bot_settings").insert({"key": "ping_failed", "value": ping_failed_value}).execute()

                print(f"[KEEP_ALIVE] ping_failed = {ping_failed_value} écrit.")
            except Exception as e:
                print(f"[KEEP_ALIVE] Impossible d'écrire ping_failed : {e}")

            await asyncio.sleep(300)  # 5 min

def run_ping_loop():
    asyncio.run(ping_loop())

# ────────────────────────────────────────────────────────────────────────────────
# 🔄 Keep Alive principal
# ────────────────────────────────────────────────────────────────────────────────
def keep_alive():
    """Lance Flask + self-ping dans 2 threads."""
    Thread(target=run_flask, daemon=True).start()
    print("[KEEP_ALIVE] Serveur Flask démarré.")

    Thread(target=run_ping_loop, daemon=True).start()
    print("[KEEP_ALIVE] Self-ping activé.")
