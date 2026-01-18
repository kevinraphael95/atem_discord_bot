# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact_pseudo.py — Commande /vaact_pseudo et !vaact_pseudo
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
    Commande /vaact_pseudo et !vaact_pseudo — Choix interactif de pseudo VAACT
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔗 Récupération des pseudos depuis Google Sheets
    # ────────────────────────────────────────────────────────────────────────────
    def get_vaact_pseudos(self) -> list[str]:
        """Récupère tous les pseudos VAACT depuis la colonne C (Joueur) uniquement"""
        url = os.getenv("VAACT_CLASSEMENT_SHEET")
        response = requests.get(url)
        response.raise_for_status()

        pseudos = set()
        reader = csv.reader(io.StringIO(response.text), delimiter="\t")
        for row in reader:
            if len(row) >= 3:
                joueur = row[2].strip()  # colonne C (index 2)
                if joueur:
                    pseudos.add(joueur)

        # Supprimer les pseudos déjà pris dans Supabase
        taken = supabase.table("profil").select("vaact_name").execute().data
        taken_set = set(item["vaact_name"] for item in taken if item["vaact_name"] != "Non défini")

        available = sorted(pseudos - taken_set, key=str.lower)
        return available

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Modal pour entrer le pseudo
    # ────────────────────────────────────────────────────────────────────────────
    class PseudoModal(Modal):
        def __init__(self, cog: "VaactPseudo"):
            super().__init__(title="Choisir ton pseudo VAACT")
            self.cog = cog
            self.pseudo_input = TextInput(
                label="Pseudo VAACT",
                placeholder="Tape ton pseudo exactement comme dans le classement",
                max_length=50
            )
            self.add_item(self.pseudo_input)

        async def on_submit(self, interaction: discord.Interaction):
            pseudo = self.pseudo_input.value.strip()
            available = self.cog.get_vaact_pseudos()

            if pseudo not in available:
                await safe_respond(interaction, f"❌ Le pseudo `{pseudo}` n'est pas disponible ou déjà pris.")
                return

            # Enregistrer le pseudo dans Supabase
            supabase.table("profil").upsert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "vaact_name": pseudo
            }).execute()

            await safe_respond(interaction, f"✅ Ton pseudo VAACT est désormais `{pseudo}` !")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Vue avec bouton pour ouvrir le modal
    # ────────────────────────────────────────────────────────────────────────────
    class PseudoView(View):
        def __init__(self, cog: "VaactPseudo"):
            super().__init__(timeout=None)
            self.cog = cog
            self.add_item(Button(label="Choisir ton pseudo", style=discord.ButtonStyle.primary, custom_id="vaact_choose"))

        @discord.ui.button(label="Choisir ton pseudo", style=discord.ButtonStyle.primary, custom_id="vaact_choose")
        async def choose_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_modal(VaactPseudo.PseudoModal(self.cog))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="vaact_pseudo",
        description="Choisis ton pseudo VAACT officiel."
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_vaact_pseudo(self, interaction: discord.Interaction):
        """Commande slash interactive pour choisir son pseudo VAACT"""
        view = VaactPseudo.PseudoView(self)
        await safe_respond(interaction, "Clique sur le bouton pour choisir ton pseudo VAACT :", view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="vaact_pseudo")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_vaact_pseudo(self, ctx: commands.Context):
        """Commande préfixe interactive pour choisir son pseudo VAACT"""
        view = VaactPseudo.PseudoView(self)
        await safe_send(ctx.channel, "Clique sur le bouton pour choisir ton pseudo VAACT :", view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = VaactPseudo(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
