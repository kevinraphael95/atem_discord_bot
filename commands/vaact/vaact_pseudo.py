# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact_pseudo.py — Commande /vaact_pseudo et !vaact_pseudo
# Objectif : Permet à un utilisateur de choisir son pseudo VAACT officiel via bouton et embed
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
import json
import os

from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class VaactPseudo(commands.Cog):
    """
    Commande /vaact_pseudo et !vaact_pseudo — Choix interactif de pseudo VAACT avec embed
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Charger le JSON des pseudos
        json_path = os.path.join("data", "vaact_pseudos.json")
        with open(json_path, "r", encoding="utf-8") as f:
            self.all_pseudos = sorted(json.load(f), key=str.lower)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔗 Récupération des pseudos disponibles
    # ────────────────────────────────────────────────────────────────────────────
    def get_vaact_pseudos(self) -> list[str]:
        """Retourne la liste des pseudos disponibles (non pris)"""
        taken = supabase.table("profil").select("user_id", "vaact_name").execute().data
        self.taken_dict = {item["user_id"]: item["vaact_name"] for item in taken if item["vaact_name"] != "Non défini"}
        taken_set = set(self.taken_dict.values())
        available = sorted([p for p in self.all_pseudos if p not in taken_set], key=str.lower)
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
                placeholder="Tape ton pseudo exactement comme dans la liste",
                max_length=50
            )
            self.add_item(self.pseudo_input)

        async def on_submit(self, interaction: discord.Interaction):
            pseudo = self.pseudo_input.value.strip()
            available = self.cog.get_vaact_pseudos()
            user_id_str = str(interaction.user.id)

            # Vérification du pseudo
            if pseudo not in self.cog.all_pseudos:
                await safe_respond(interaction, f"❌ Le pseudo `{pseudo}` n'existe pas dans la liste officielle.")
                return

            # Si le pseudo est déjà pris
            if pseudo in self.cog.taken_dict.values():
                if self.cog.taken_dict.get(user_id_str) == pseudo:
                    await safe_respond(interaction, f"✅ Tu utilises déjà le pseudo `{pseudo}` !")
                else:
                    await safe_respond(interaction, f"❌ Le pseudo `{pseudo}` est déjà pris par un autre joueur.")
                return

            # Enregistrer dans Supabase
            supabase.table("profil").upsert({
                "user_id": user_id_str,
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

        @discord.ui.button(label="Choisir ton pseudo", style=discord.ButtonStyle.primary, custom_id="vaact_choose")
        async def choose_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_modal(VaactPseudo.PseudoModal(self.cog))

    # ────────────────────────────────────────────────────────────────────────────────
    # 🔹 Embed des pseudos ultra-compact
    # ────────────────────────────────────────────────────────────────────────────────
    def create_pseudos_embed(self) -> discord.Embed:
        """Crée un embed listant tous les pseudos du JSON sur une seule ligne"""
        description = ", ".join(self.all_pseudos)  # tous les pseudos séparés par des virgules
    
        embed = discord.Embed(
            title="Liste des pseudos VAACT officiels",
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Tape ton pseudo exactement comme dans la liste ci-dessus.")
        return embed


    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="vaact_pseudo",
        description="Choisis ton pseudo VAACT officiel via bouton et embed."
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_vaact_pseudo(self, interaction: discord.Interaction):
        """Commande slash interactive pour choisir son pseudo VAACT"""
        self.get_vaact_pseudos()
        embed = self.create_pseudos_embed()
        view = VaactPseudo.PseudoView(self)
        await safe_respond(interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="vaact_pseudo")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_vaact_pseudo(self, ctx: commands.Context):
        """Commande préfixe interactive pour choisir son pseudo VAACT"""
        self.get_vaact_pseudos()
        embed = self.create_pseudos_embed()
        view = VaactPseudo.PseudoView(self)
        await safe_send(ctx.channel, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = VaactPseudo(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
