# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi_date.py
# Objectif : Afficher / modifier / supprimer la date et le lieu du tournoi (SQLite)
# Catégorie : 🧠 VAACT
# Accès : Admin
# Cooldown : 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

from utils.discord_utils import safe_send
from utils.init_db import get_conn  # <-- DB centralisée

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
        conn = get_conn("tournoi")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tournoi_info SET prochaine_date = ?, lieu = ? WHERE id = 1",
            (dt.isoformat(), self.lieu.value)
        )
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
        conn = get_conn("tournoi")
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
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiDate(commands.Cog):
    """Commande /tournoidate et !tournoidate — Affiche et gère la date du tournoi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_tournoi_date(self, channel: discord.abc.Messageable):
        conn = get_conn("tournoi")
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

        await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="tournoidate",
        description="(Admin) 🛠️ Gérer la date du tournoi VAACT."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_tournoidate(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_tournoi_date(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="tournoidate", aliases=["settournoi"], help="(Admin) 🛠️ Gérer la date du tournoi VAACT.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_tournoidate(self, ctx: commands.Context):
        await self._send_tournoi_date(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiDate(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
