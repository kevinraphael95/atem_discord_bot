# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi.py — Commande interactive !tournoi
# Objectif : Affiche la date et le lieu du prochain tournoi à partir de Supabase
# Catégorie : 🧠 VAACT
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import os
from datetime import datetime
import locale

from utils.discord_utils import safe_send
from utils.supabase_client import supabase  # ✅ utilisation du client central

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
SHEET_CSV_URL = os.getenv("SHEET_CSV_URL")

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiCommand(commands.Cog):
    """📌 Affiche la date et le lieu du prochain tournoi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="tournoi",
        help="📅 Affiche la date et le lieu du prochain tournoi VAACT.",
        description="Récupère la date et le lieu depuis Supabase."
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def tournoi(self, ctx: commands.Context):
        """Commande principale !tournoi"""
        try:
            # ✅ Lecture de la seule ligne (un seul tournoi possible)
            result = supabase.table("tournoi_info").select("prochaine_date, lieu").execute()
            data = result.data
        except Exception as e:
            print(f"[ERREUR SUPABASE] {e}")
            await safe_send(ctx, "❌ Impossible de se connecter à Supabase.")
            return

        if not data or not data[0].get("prochaine_date"):
            await safe_send(ctx, "📭 Aucun tournoi prévu pour le moment.")
            return

        # Formatage de la date
        iso_date = data[0]["prochaine_date"]
        lieu = data[0].get("lieu", "Non renseigné")
        try:
            dt = datetime.fromisoformat(iso_date)
            date_formatee = dt.strftime('%d %B %Y à %Hh%M')
        except Exception:
            date_formatee = iso_date  # fallback brut

        # Embed principal
        embed = discord.Embed(
            title="📅 Prochain tournoi VAACT",
            description=(
                f"📆 **Date** : {date_formatee}\n"
                f"📍 **Lieu** : {lieu}"
            ),
            color=discord.Color.gold()
        )

        # Ajouter bouton pour le lien CSV si défini
        view = None
        if SHEET_CSV_URL:
            class DeckButton(discord.ui.View):
                def __init__(self):
                    super().__init__()
                    self.add_item(discord.ui.Button(
                        label="📋 Voir les decks",
                        url=SHEET_CSV_URL
                    ))
            view = DeckButton()

        await safe_send(ctx, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
