# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi_rappel.py — Tâche quotidienne qui envoie les rappels de tournoi
# Objectif : Envoyer un MP 3 jours avant la date du tournoi
# Catégorie : 🔁 Tâches planifiées
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import tasks, commands
import aiohttp
import os
from datetime import datetime, timedelta

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class TournoiRappelTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rappel_tournoi.start()

    def cog_unload(self):
        self.rappel_tournoi.cancel()

    @tasks.loop(hours=24)
    async def rappel_tournoi(self):
        """Tâche qui s'exécute une fois par jour pour envoyer un rappel 3 jours avant le tournoi."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("[❌] Clés Supabase manquantes.")
            return

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                # Récupération de la date du prochain tournoi
                url = f"{SUPABASE_URL}/rest/v1/tournoi_info?select=prochaine_date&order=id.desc&limit=1"
                async with session.get(url, headers=headers) as response:
                    tournoi_data = await response.json()

                if not tournoi_data or not tournoi_data[0].get("prochaine_date"):
                    print("📭 Aucun tournoi trouvé.")
                    return

                tournoi_date = datetime.strptime(tournoi_data[0]["prochaine_date"], "%Y-%m-%d").date()
                today = datetime.utcnow().date()

                if tournoi_date != today + timedelta(days=3):
                    print("⏳ Ce n’est pas encore le jour d’envoyer les rappels.")
                    return

                # Récupération des utilisateurs à rappeler
                async with session.get(f"{SUPABASE_URL}/rest/v1/rappels_tournoi", headers=headers) as r:
                    users = await r.json()

                for user in users:
                    user_id = int(user["user_id"])
                    member = await self.bot.fetch_user(user_id)
                    try:
                        await member.send("📅 Rappel : Le tournoi commence dans **3 jours** ! Prépare ton deck 🧠")
                    except discord.Forbidden:
                        print(f"⚠️ Impossible d’envoyer un message à {user_id} (DM bloqués).")

                # Optionnel : vider la table après envoi
                await session.request(
                    method="DELETE",
                    url=f"{SUPABASE_URL}/rest/v1/rappels_tournoi",
                    headers={**headers, "Content-Type": "application/json"},
                )

                print("✅ Tous les rappels ont été envoyés.")

        except Exception as e:
            print(f"[ERREUR RAPPEL TOURNOI] {e}")

    @rappel_tournoi.before_loop
    async def before_rappel(self):
        await self.bot.wait_until_ready()

# 🔌 Setup
async def setup(bot):
    await bot.add_cog(Tourno
iRappelTask(bot))
