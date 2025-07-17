# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi_rappel.py — Rappel automatique des tournois
# Objectif : Envoie un MP aux utilisateurs inscrits 3 jours avant la date du tournoi
# Catégorie : Autre
# Accès : Privé (exécuté automatiquement, sans commande utilisateur)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands, tasks
import aiohttp
import os
from datetime import datetime, timedelta
from utils.discord_utils import safe_send  # Pour les DM

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — tâche automatique quotidienne
# ────────────────────────────────────────────────────────────────────────────────
class TournoiRappelTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rappel_tournoi.start()

    def cog_unload(self):
        self.rappel_tournoi.cancel()

    # 🔁 Tâche planifiée — exécution quotidienne
    @tasks.loop(hours=24)
    async def rappel_tournoi(self):
        """Envoie un rappel de tournoi 3 jours avant la date prévue."""
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")

        if not SUPABASE_URL or not SUPABASE_KEY:
            print("❌ Clés Supabase manquantes. Tâche annulée.")
            return

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                # 📅 Récupération de la prochaine date de tournoi
                url = f"{SUPABASE_URL}/rest/v1/tournoi_info?select=prochaine_date&order=id.desc&limit=1"
                async with session.get(url, headers=headers) as resp:
                    tournoi_data = await resp.json()

                if not tournoi_data or not tournoi_data[0].get("prochaine_date"):
                    print("📭 Aucun tournoi planifié.")
                    return

                tournoi_date = datetime.strptime(tournoi_data[0]["prochaine_date"], "%Y-%m-%d").date()
                today = datetime.utcnow().date()

                # 📆 Si ce n’est pas 3 jours avant le tournoi, on quitte
                if tournoi_date != today + timedelta(days=3):
                    print("⏳ Pas encore l'heure d'envoyer les rappels.")
                    return

                # 📤 Récupération des utilisateurs à notifier
                async with session.get(f"{SUPABASE_URL}/rest/v1/rappels_tournoi", headers=headers) as r:
                    users = await r.json()

                for user in users:
                    try:
                        user_id = int(user["user_id"])
                        member = await self.bot.fetch_user(user_id)
                        await safe_send(
                            member,
                            "📅 **Rappel :** Le tournoi commence dans **3 jours** ! Prépare ton deck 🧠"
                        )
                    except Exception as e:
                        print(f"⚠️ Erreur lors de l'envoi du rappel à {user.get('user_id')} : {e}")

                # 🧹 Nettoyage de la table des rappels
                await session.request(
                    method="DELETE",
                    url=f"{SUPABASE_URL}/rest/v1/rappels_tournoi",
                    headers={**headers, "Content-Type": "application/json"},
                )

                print("✅ Tous les rappels ont été envoyés avec succès.")

        except Exception as e:
            print(f"[ERREUR RAPPEL TOURNOI] {e}")

    # ⏳ Attente que le bot soit prêt
    @rappel_tournoi.before_loop
    async def before_rappel(self):
        await self.bot.wait_until_ready()

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(TournoiRappelTask(bot))
