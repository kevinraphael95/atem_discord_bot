# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact_pseudo.py — Commande simple /vaact_pseudo et !vaact_pseudo
# Objectif : Permet à un utilisateur de choisir son pseudo VAACT officiel via modal
# Catégorie : VAACT
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import csv
import io
import os
import requests

from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class VaactPseudo(commands.Cog):
    """
    Commande /vaact_pseudo et !vaact_pseudo — Permet de choisir un pseudo VAACT officiel via modal
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔗 Récupération des pseudos depuis Google Sheets
    # ────────────────────────────────────────────────────────────────────────────
    def get_vaact_pseudos(self) -> list[str]:
        """Récupère tous les pseudos VAACT depuis le CSV et renvoie une liste unique triée"""
        url = os.getenv("VAACT_CLASSEMENT_SHEET")
        response = requests.get(url)
        response.raise_for_status()
        pseudos = set()
        reader = csv.reader(io.StringIO(response.text))
        next(reader, None)  # ignore l'en-tête
        for row in reader:
            for cell in row:
                cell = cell.strip()
                if cell and cell != "Joueur":
                    pseudos.add(cell)
        return sorted(pseudos, key=str.lower)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Modal pour entrer un pseudo
    # ────────────────────────────────────────────────────────────────────────────
    class VaactModal(Modal):
        def __init__(self, user_id: int, available_pseudos: list[str]):
            super().__init__(title="Choisissez votre pseudo VAACT")
            self.user_id = user_id
            self.available_pseudos = available_pseudos
            self.pseudo_input = TextInput(
                label="Entrez votre pseudo",
                placeholder="Exemple : Shinram",
                max_length=50
            )
            self.add_item(self.pseudo_input)

        async def on_submit(self, interaction: discord.Interaction):
            pseudo = self.pseudo_input.value.strip()
            if pseudo not in self.available_pseudos:
                await safe_respond(interaction, f"❌ Le pseudo **{pseudo}** n'est pas disponible.", ephemeral=True)
                return

            # Vérifie si le pseudo est déjà pris
            existing = supabase.table("profil").select("vaact_name").eq("vaact_name", pseudo).execute()
            if existing.data:
                await safe_respond(interaction, f"❌ Le pseudo **{pseudo}** est déjà pris.", ephemeral=True)
                return

            # Sauvegarde le pseudo choisi
            supabase.table("profil").update({"vaact_name": pseudo}).eq("user_id", str(self.user_id)).execute()
            await safe_respond(interaction, f"✅ Votre pseudo VAACT est maintenant **{pseudo}** !", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Vue avec bouton pour entrer le pseudo
    # ────────────────────────────────────────────────────────────────────────────
    class VaactView(View):
        def __init__(self, user_id: int, available_pseudos: list[str]):
            super().__init__(timeout=120)
            self.user_id = user_id
            self.available_pseudos = available_pseudos
            self.add_item(
                Button(label="Entrer votre pseudo", style=discord.ButtonStyle.primary, custom_id="enter_vaact")
            )

        @discord.ui.button(label="Entrer votre pseudo", style=discord.ButtonStyle.primary)
        async def enter_button(self, button: Button, interaction: discord.Interaction):
            modal = VaactPseudo.VaactModal(self.user_id, self.available_pseudos)
            await interaction.response.send_modal(modal)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="vaact_pseudo",
        description="Choisissez votre pseudo VAACT officiel"
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_vaact_pseudo(self, interaction: discord.Interaction):
        """Commande slash pour afficher la liste des pseudos et bouton modal"""
        pseudos = self.get_vaact_pseudos()
        taken = [p["vaact_name"] for p in supabase.table("profil").select("vaact_name").execute().data if p["vaact_name"] and p["vaact_name"] != "Non défini"]
        available = [p for p in pseudos if p not in taken]
        if not available:
            await safe_respond(interaction, "❌ Tous les pseudos sont déjà pris !", ephemeral=True)
            return
        pseudo_list = ", ".join(available[:50]) + ("..." if len(available) > 50 else "")
        view = self.VaactView(interaction.user.id, available)
        await safe_respond(interaction, f"**Pseudos disponibles :**\n{pseudo_list}", view=view, ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="vaact_pseudo")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_vaact_pseudo(self, ctx: commands.Context):
        """Commande préfixe pour afficher la liste des pseudos et bouton modal"""
        pseudos = self.get_vaact_pseudos()
        taken = [p["vaact_name"] for p in supabase.table("profil").select("vaact_name").execute().data if p["vaact_name"] and p["vaact_name"] != "Non défini"]
        available = [p for p in pseudos if p not in taken]
        if not available:
            await safe_send(ctx.channel, "❌ Tous les pseudos sont déjà pris !")
            return
        pseudo_list = ", ".join(available[:50]) + ("..." if len(available) > 50 else "")
        view = self.VaactView(ctx.author.id, available)
        await safe_send(ctx.channel, f"**Pseudos disponibles :**\n{pseudo_list}", view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = VaactPseudo(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
