# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact_pseudo.py — Commande simple /vaact_pseudo et !vaact_pseudo
# Objectif : Permet à un utilisateur de choisir son pseudo VAACT officiel
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
from discord.ui import View, Select
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
    Commande /vaact_pseudo et !vaact_pseudo — Permet de choisir un pseudo VAACT officiel
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔗 Récupération des pseudos depuis Google Sheets
    # ────────────────────────────────────────────────────────────────────────────
    def get_vaact_pseudos(self) -> list[str]:
        """Récupère la liste des pseudos VAACT depuis la colonne 'Joueur' du CSV"""
        url = os.getenv("VAACT_CLASSEMENT_SHEET")
        response = requests.get(url)
        response.raise_for_status()
        pseudos = []
        reader = csv.reader(io.StringIO(response.text))
        next(reader, None)  # ignore l'en-tête
        for row in reader:
            if len(row) >= 3 and row[2].strip():
                pseudos.append(row[2].strip())  # 3ᵉ colonne = "Joueur"
        return pseudos

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Vue interactive pour sélectionner un pseudo
    # ────────────────────────────────────────────────────────────────────────────
    class VaactSelect(Select):
        def __init__(self, available_pseudos: list[str], user_id: int):
            options = [discord.SelectOption(label=p, value=p) for p in available_pseudos[:25]]
            super().__init__(placeholder="Choisissez votre pseudo VAACT", options=options)
            self.user_id = user_id

        async def callback(self, interaction: discord.Interaction):
            existing = (
                supabase.table("profil").select("vaact_name")
                .eq("vaact_name", self.values[0])
                .execute()
            )
            if existing.data:
                await safe_respond(interaction, f"❌ Le pseudo **{self.values[0]}** est déjà pris.", ephemeral=True)
                return

            supabase.table("profil").update({"vaact_name": self.values[0]}).eq("user_id", str(self.user_id)).execute()
            await safe_respond(interaction, f"✅ Votre pseudo VAACT est maintenant **{self.values[0]}** !", ephemeral=True)
            self.view.stop()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Vue complète
    # ────────────────────────────────────────────────────────────────────────────
    class VaactView(View):
        def __init__(self, available_pseudos: list[str], user_id: int):
            super().__init__(timeout=60)
            self.add_item(VaactPseudo.VaactSelect(available_pseudos, user_id))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="vaact_pseudo",
        description="Choisissez votre pseudo VAACT officiel"
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_vaact_pseudo(self, interaction: discord.Interaction):
        """Commande slash pour choisir un pseudo VAACT"""
        pseudos = self.get_vaact_pseudos()
        taken = [
            p["vaact_name"]
            for p in supabase.table("profil").select("vaact_name").execute().data
            if p["vaact_name"] and p["vaact_name"] != "Non défini"
        ]
        available = [p for p in pseudos if p not in taken]
        if not available:
            await safe_respond(interaction, "❌ Tous les pseudos sont déjà pris !", ephemeral=True)
            return
        view = self.VaactView(available, interaction.user.id)
        await safe_respond(interaction, "Sélectionnez votre pseudo VAACT :", view=view, ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="vaact_pseudo")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_vaact_pseudo(self, ctx: commands.Context):
        """Commande préfixe pour choisir un pseudo VAACT"""
        pseudos = self.get_vaact_pseudos()
        taken = [
            p["vaact_name"]
            for p in supabase.table("profil").select("vaact_name").execute().data
            if p["vaact_name"] and p["vaact_name"] != "Non défini"
        ]
        available = [p for p in pseudos if p not in taken]
        if not available:
            await safe_send(ctx.channel, "❌ Tous les pseudos sont déjà pris !")
            return
        view = self.VaactView(available, ctx.author.id)
        await safe_send(ctx.channel, "Sélectionnez votre pseudo VAACT :", view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = VaactPseudo(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
