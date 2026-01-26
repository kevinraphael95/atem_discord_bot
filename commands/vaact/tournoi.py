# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi.py — Commande interactive !tournoi
# Objectif : Affiche la date et le lieu du prochain tournoi (SQLite)
# Catégorie : 🧠 VAACT
# Accès : Public
# Base : SQLite locale
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
from datetime import datetime
import sqlite3

import discord
from discord.ext import commands

from utils.discord_utils import safe_send

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
        cursor.execute("INSERT INTO tournoi_info (id, prochaine_date, lieu) VALUES (1, NULL, NULL)")
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
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiCommand(commands.Cog):
    """📌 Affiche la date et le lieu du prochain tournoi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    @commands.command(
        name="tournoi",
        help="📅 Affiche la date et le lieu du prochain tournoi VAACT.",
        description="Récupère la date et le lieu depuis SQLite locale."
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def tournoi(self, ctx: commands.Context):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT prochaine_date, lieu FROM tournoi_info WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            await safe_send(ctx, "📭 Aucun tournoi prévu pour le moment.")
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

        await safe_send(ctx, embed=embed, files=files)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
