# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi_date.py — Commande interactive !tournoidate
# Objectif : Afficher / modifier / supprimer la date et le lieu du tournoi (SQLite)
# Catégorie : 🧠 VAACT
# Accès : Admin
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
from discord.ui import View, Button, Modal, TextInput

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
# 📝 UI — Modal Date + Lieu
# ────────────────────────────────────────────────────────────────────────────────
class TournoiDateModal(Modal, title="📅 Modifier le tournoi"):
    date = TextInput(label="Date du tournoi", placeholder="JJ/MM/AAAA HH:MM", required=True)
    lieu = TextInput(label="Lieu du tournoi", placeholder="Ex: Paris / Discord / Salle XYZ", required=True, max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            dt = datetime.strptime(self.date.value, "%d/%m/%Y %H:%M")
        except ValueError:
            return await interaction.response.send_message(
                "❌ Format invalide.\nUtilise **JJ/MM/AAAA HH:MM**",
                ephemeral=True
            )
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE tournoi_info SET prochaine_date = ?, lieu = ? WHERE id = 1", (dt.isoformat(), self.lieu.value))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ **Tournoi mis à jour avec succès**", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Boutons Embed
# ────────────────────────────────────────────────────────────────────────────────
class EditDateButton(Button):
    def __init__(self):
        super().__init__(label="Ajouter / Modifier", style=discord.ButtonStyle.primary, emoji="✏️")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TournoiDateModal())

class DeleteDateButton(Button):
    def __init__(self):
        super().__init__(label="Supprimer", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def callback(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE tournoi_info SET prochaine_date = NULL, lieu = NULL WHERE id = 1")
        conn.commit()
        conn.close()
        await interaction.response.send_message("🗑️ **La date du tournoi a été supprimée.**", ephemeral=True)

class TournoiDateView(View):
    def __init__(self, has_date: bool):
        super().__init__(timeout=180)
        self.add_item(EditDateButton())
        if has_date:
            self.add_item(DeleteDateButton())

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — !tournoidate (admin)
# ────────────────────────────────────────────────────────────────────────────────
class TournoiDate(commands.Cog):
    """Commande !tournoidate — Affiche et gère la date du tournoi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    @commands.command(name="tournoidate", aliases=["settournoi"], help="(Admin) 🛠️ Gérer la date du tournoi VAACT.", description="Affiche la date actuelle et permet de l'ajouter, modifier ou supprimer.")
    @commands.has_permissions(administrator=True)
    async def tournoidate(self, ctx: commands.Context):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tournoi_info WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        info = {"prochaine_date": None, "lieu": None}
        if row:
            info = {"prochaine_date": row[1], "lieu": row[2]}

        embed = discord.Embed(title="🏆 Tournoi VAACT", color=discord.Color.blurple())
        if info["prochaine_date"]:
            dt = datetime.fromisoformat(info["prochaine_date"])
            embed.add_field(name="📅 Date", value=dt.strftime("%d/%m/%Y à %Hh%M"), inline=False)
            embed.add_field(name="📍 Lieu", value=info["lieu"] or "Non précisé", inline=False)
            view = TournoiDateView(has_date=True)
        else:
            embed.description = "❌ **Aucun tournoi programmé pour le moment.**"
            view = TournoiDateView(has_date=False)

        await safe_send(ctx, embed=embed, view=view)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiDate(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
