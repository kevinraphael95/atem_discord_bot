# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi.py
# Objectif : Affiche la date et le lieu du prochain tournoi (SQLite) avec bouton Google Sheet
# Catégorie : 🧠 VAACT
# Accès : Public
# Cooldown : 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
from datetime import datetime
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send

SHEET_CSV_URL = os.getenv("SHEET_CSV_URL")

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Configuration SQLite
# ────────────────────────────────────────────────────────────────────────────────
DB_PATH = "database/tournoi.db"
os.makedirs("database", exist_ok=True)

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournoi_info (
            id INTEGER PRIMARY KEY,
            prochaine_date TEXT,
            lieu TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM tournoi_info")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO tournoi_info (id, prochaine_date, lieu) VALUES (1, NULL, NULL)"
        )
    conn.commit()
    conn.close()

# ────────────────────────────────────────────────────────────────────────────────
# 🗓️ Mois en français
# ────────────────────────────────────────────────────────────────────────────────
MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

# ────────────────────────────────────────────────────────────────────────────────
# 🖼️ Logo VAACT
# ────────────────────────────────────────────────────────────────────────────────
VAACT_LOGO_PATH = "data/images/vaact_logo.png"

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton Google Sheet
# ────────────────────────────────────────────────────────────────────────────────
class DecksButtonView(View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(DecksButton(url))

class DecksButton(Button):
    def __init__(self, url: str):
        super().__init__(
            label="📋 Voir les decks",
            style=discord.ButtonStyle.link,
            url=url
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiCommand(commands.Cog):
    """
    Commande /tournoi et !tournoi — Affiche la date et le lieu du prochain tournoi
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_tournoi(self, channel: discord.abc.Messageable):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT prochaine_date, lieu FROM tournoi_info WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            await safe_send(channel, "📭 Aucun tournoi prévu pour le moment.")
            return

        dt = datetime.fromisoformat(row[0])
        mois = MOIS_FR[dt.month - 1]
        date_formatee = f"{dt.day} {mois} {dt.year} à {dt.hour:02d}h{dt.minute:02d}"
        lieu = row[1] or "Non renseigné"

        embed = discord.Embed(
            title="🏆 Prochain tournoi VAACT",
            description=f"📆 **Date** : {date_formatee}\n📍 **Lieu** : {lieu}",
            color=discord.Color.gold()
        )

        files = []
        if os.path.exists(VAACT_LOGO_PATH):
            file = discord.File(VAACT_LOGO_PATH, filename="vaact_logo.png")
            embed.set_thumbnail(url="attachment://vaact_logo.png")
            files.append(file)

        view = DecksButtonView(SHEET_CSV_URL) if SHEET_CSV_URL else None

        await safe_send(channel, embed=embed, files=files, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="tournoi",
        description="Affiche la date et le lieu du prochain tournoi VAACT."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_tournoi(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_tournoi(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="tournoi", help="Affiche la date et le lieu du prochain tournoi VAACT.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_tournoi(self, ctx: commands.Context):
        await self._send_tournoi(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
