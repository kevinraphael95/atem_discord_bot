# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi.py — Commande interactive !tournoi
# Objectif : Affiche la date du prochain tournoi à partir de Supabase + système de rappel
# Catégorie : 🧠 VAACT
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import os
from datetime import datetime
import locale

from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌍 Configuration régionale (français)
# ────────────────────────────────────────────────────────────────────────────────
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR')
    except locale.Error:
        pass

# ────────────────────────────────────────────────────────────────────────────────
# 🔐 Variables d’environnement
# ────────────────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SHEET_CSV_URL = os.getenv("SHEET_CSV_URL2")

EMOJI_RAPPEL = "🛎️"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiCommand(commands.Cog):
    """
    📌 Affiche la date du prochain tournoi et permet de s’inscrire au rappel.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="tournoi",
        help="📅 Affiche la date du prochain tournoi VAACT.",
        description="Récupère la date depuis Supabase et permet aux utilisateurs de s’inscrire au rappel."
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def tournoi(self, ctx: commands.Context):
        """Commande principale !tournoi"""
        if not SUPABASE_URL or not SUPABASE_KEY:
            await safe_send(ctx, "❌ Configuration manquante (SUPABASE_URL ou SUPABASE_KEY).")
            return

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{SUPABASE_URL}/rest/v1/tournoi_info?select=prochaine_date&order=id.desc&limit=1"
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        await safe_send(ctx, "❌ Erreur lors de la récupération de la date.")
                        return
                    data = await response.json()
        except Exception as e:
            print(f"[ERREUR SUPABASE] {e}")
            await safe_send(ctx, "❌ Impossible de se connecter à Supabase.")
            return

        if not data or not data[0].get("prochaine_date"):
            await safe_send(ctx, "📭 Aucun tournoi prévu pour le moment.")
            return

        # Formatage date
        iso_date = data[0]["prochaine_date"]
        try:
            dt = datetime.fromisoformat(iso_date)
            date_formatee = dt.strftime('%d %B %Y à %Hh%M')
        except Exception:
            date_formatee = iso_date  # fallback brut

        # Embed principal
        embed = discord.Embed(
            title="📅 Prochain tournoi",
            description=(
                f"📆 **Date du prochain tournoi VAACT** :\n"
                f"➡️ **{date_formatee}**\n\n"
                f"📋 **Decks disponibles :**\n"
                f"[Voir la liste]({SHEET_CSV_URL})"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Réagis avec {EMOJI_RAPPEL} pour recevoir un rappel 3 jours avant. (Pas encore actif)")

        message = await safe_send(ctx, embed=embed)
        await message.add_reaction(EMOJI_RAPPEL)

        def check(reaction, user):
            return (
                reaction.message.id == message.id and
                str(reaction.emoji) == EMOJI_RAPPEL and
                not user.bot
            )

        # Gestion des réactions (15 minutes)
        try:
            while True:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=900.0, check=check)

                async with aiohttp.ClientSession() as session:
                    headers["Prefer"] = "resolution=merge-duplicates"
                    url_check = f"{SUPABASE_URL}/rest/v1/rappels_tournoi?user_id=eq.{user.id}"
                    async with session.get(url_check, headers=headers) as r:
                        exists = await r.json()

                    if exists:
                        try:
                            await user.send("🛎️ Tu es déjà inscrit pour recevoir un rappel.")
                        except discord.Forbidden:
                            await safe_send(ctx, f"{user.mention}, je ne peux pas t’envoyer de message privé.")
                        continue

                    # Inscription
                    url_insert = f"{SUPABASE_URL}/rest/v1/rappels_tournoi"
                    async with session.post(
                        url_insert,
                        headers={**headers, "Content-Type": "application/json"},
                        json={"user_id": str(user.id)}
                    ) as resp:
                        if resp.status in [200, 201]:
                            try:
                                await user.send("✅ Tu recevras un rappel 3 jours avant le tournoi !")
                            except discord.Forbidden:
                                await safe_send(ctx, f"{user.mention}, je ne peux pas t’envoyer de MP.")
                        else:
                            print("[SUPABASE INSERT ERROR]", await resp.text())

        except Exception as e:
            print("[Réaction timeout ou erreur]", e)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
