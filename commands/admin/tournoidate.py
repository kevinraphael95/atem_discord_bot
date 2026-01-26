# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi_date.py — Commande interactive !tournoidate
# Objectif : Afficher / modifier / supprimer la date et le lieu du tournoi (TinyDB)
# Catégorie : 🧠 VAACT
# Accès : Modérateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
from datetime import datetime

import discord
from discord.ext import commands
from discord.ui import View, Button
from tinydb import TinyDB, Query

from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Configuration TinyDB
# ────────────────────────────────────────────────────────────────────────────────
DB_FOLDER = os.path.join("db")
os.makedirs(DB_FOLDER, exist_ok=True)

DB_PATH = os.path.join(DB_FOLDER, "tournoi.json")
db = TinyDB(DB_PATH)
tournoi_table = db.table("tournoi_info")
Tournoi = Query()

# ────────────────────────────────────────────────────────────────────────────────
# 📝 UI — Modal Date + Lieu
# ────────────────────────────────────────────────────────────────────────────────
class TournoiDateModal(discord.ui.Modal, title="📅 Modifier le tournoi"):

    date = discord.ui.TextInput(
        label="Date du tournoi",
        placeholder="JJ/MM/AAAA HH:MM",
        required=True
    )

    lieu = discord.ui.TextInput(
        label="Lieu du tournoi",
        placeholder="Ex: Paris / Discord / Salle XYZ",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            dt = datetime.strptime(self.date.value, "%d/%m/%Y %H:%M")
        except ValueError:
            return await interaction.response.send_message(
                "❌ Format invalide.\nUtilise **JJ/MM/AAAA HH:MM**",
                ephemeral=True
            )

        # ────────────────────────────────────────────────────────────────────────────
        # 🔹 Insertion ou mise à jour TinyDB
        # ────────────────────────────────────────────────────────────────────────────
        if tournoi_table.contains(Tournoi.id == 1):
            tournoi_table.update(
                {"prochaine_date": dt.isoformat(), "lieu": self.lieu.value},
                Tournoi.id == 1
            )
        else:
            tournoi_table.insert({
                "id": 1,
                "prochaine_date": dt.isoformat(),
                "lieu": self.lieu.value
            })

        await interaction.response.send_message(
            "✅ **Tournoi mis à jour avec succès**",
            ephemeral=True
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Boutons Embed
# ────────────────────────────────────────────────────────────────────────────────
class TournoiDateView(View):
    def __init__(self, has_date: bool):
        super().__init__(timeout=180)
        self.add_item(EditDateButton())
        if has_date:
            self.add_item(DeleteDateButton())


class EditDateButton(Button):
    def __init__(self):
        super().__init__(
            label="Ajouter / Modifier",
            style=discord.ButtonStyle.primary,
            emoji="✏️"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TournoiDateModal())


class DeleteDateButton(Button):
    def __init__(self):
        super().__init__(
            label="Supprimer",
            style=discord.ButtonStyle.danger,
            emoji="🗑️"
        )

    async def callback(self, interaction: discord.Interaction):
        tournoi_table.remove(Tournoi.id == 1)
        await interaction.response.send_message(
            "🗑️ **La date du tournoi a été supprimée.**",
            ephemeral=True
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiDate(commands.Cog):
    """
    Commande !tournoidate — Affiche et gère la date du tournoi.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="tournoidate",
        aliases=["settournoi"],
        help="(Admin) 🛠️ Gérer la date du tournoi VAACT.",
        description="Affiche la date actuelle et permet de l'ajouter, modifier ou supprimer."
    )
    @commands.has_permissions(administrator=True)
    async def tournoidate(self, ctx: commands.Context):
        data = tournoi_table.get(Tournoi.id == 1)

        embed = discord.Embed(
            title="🏆 Tournoi VAACT",
            color=discord.Color.blurple()
        )

        if data and data.get("prochaine_date"):
            dt = datetime.fromisoformat(data["prochaine_date"])
            embed.add_field(
                name="📅 Date",
                value=dt.strftime("%d/%m/%Y à %Hh%M"),
                inline=False
            )
            embed.add_field(
                name="📍 Lieu",
                value=data.get("lieu") or "Non précisé",
                inline=False
            )
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
