# ────────────────────────────────────────────────────────────────────────────────
# 📌 profil.py — Commande pour afficher le profil VAACT d’un utilisateur
# Objectif : Affiche les informations enregistrées dans la table "profil" et permet
#            de choisir son pseudo VAACT parmi ceux du tournoi
# Catégorie : Profil
# Accès : Public
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_respond
import aiohttp
import csv
import io
import os

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ProfilCommand(commands.Cog):
    """Commande /profil et !profil — Affiche le profil complet et permet de choisir
       son pseudo VAACT parmi les pseudos du tournoi"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sheet_csv_url = os.getenv("VAACT_CLASSEMENT_SHEET")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne : récupérer les pseudos depuis Google Sheet
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_sheet_pseudos(self):
        async with aiohttp.ClientSession() as session:
            resp = await session.get(self.sheet_csv_url)
            if resp.status != 200:
                return []
            text = await resp.text()
            rows = list(csv.reader(io.StringIO(text)))
            return [row[2].strip() for row in rows[2:] if len(row) > 2 and row[2].strip()]

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne : envoyer le profil
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_profil(self, ctx_or_interaction, author, guild, target_user=None):
        """
        Affiche le profil d'un utilisateur.
        - ctx_or_interaction : message ou interaction
        - author : utilisateur qui demande
        - guild : serveur
        - target_user : utilisateur ciblé (ou None pour l’auteur)
        """
        user = target_user or author
        user_id = str(user.id)

        # 🔹 Récupération du profil dans la DB
        profil_data = supabase.table("profil").select("*").eq("user_id", user_id).execute()
        if profil_data.data:
            profil = profil_data.data[0]
            cartefav = profil.get("cartefav", "Aucune")
            vaact_name = profil.get("vaact_name", None)
            fav_decks = profil.get("fav_decks_vaact", [])
            decks_text = ", ".join(fav_decks) if fav_decks else "Aucun"
        else:
            # Crée un profil vide si inexistant
            supabase.table("profil").insert({
                "user_id": user_id,
                "username": user.name,
                "cartefav": "Aucune"
            }).execute()
            vaact_name = None
            cartefav = "Aucune"
            decks_text = "Aucun"

        # 🔹 Construction de l'embed
        color = discord.Color.green() if vaact_name else discord.Color.blue()
        embed = discord.Embed(
            title=f"__**Profil de {user.display_name}**__",
            description=(
                f"**Carte préférée** : {cartefav}\n"
                f"**Pseudo VAACT** : {vaact_name or 'Non défini'}\n"
                f"**Decks VAACT préférés** : {decks_text}"
            ),
            color=color
        )
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(text=f"Utilisateur : {user.name} ({user.id})")

        # 🔹 Si pseudo non défini, proposer un menu Select
        view = None
        if not vaact_name:
            sheet_pseudos = await self.fetch_sheet_pseudos()
            # 🔹 Supprimer pseudos déjà pris
            taken = [p["vaact_name"] for p in supabase.table("profil").select("vaact_name").not_("vaact_name", "is", None).execute().data]
            available = [p for p in sheet_pseudos if p not in taken]

            if available:
                options = [discord.SelectOption(label=p) for p in available]

                class VAACSelect(Select):
                    def __init__(self):
                        super().__init__(
                            placeholder="Choisis ton pseudo VAACT",
                            min_values=1,
                            max_values=1,
                            options=options
                        )

                    async def callback(self, interaction: discord.Interaction):
                        selected = self.values[0]
                        # Met à jour Supabase
                        supabase.table("profil").update({"vaact_name": selected}).eq("user_id", user_id).execute()
                        await interaction.response.send_message(
                            f"✅ Ton pseudo VAACT a été défini : **{selected}**", ephemeral=True
                        )
                        self.disabled = True
                        await interaction.message.edit(view=self.view)

                class VAACSelectView(View):
                    def __init__(self):
                        super().__init__(timeout=120)
                        self.add_item(VAACSelect())

                view = VAACSelectView()

        # 🔹 Envoi selon le contexte
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, view=view)
        else:
            await safe_send(ctx_or_interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH /profil
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="profil", description="📋 Affiche le profil et permet de choisir son pseudo VAACT")
    async def slash_profil(self, interaction: discord.Interaction, member: discord.Member = None):
        try:
            await self._send_profil(interaction, interaction.user, interaction.guild, member)
        except Exception as e:
            print(f"[ERREUR /profil] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX !profil
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="profil")
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_profil(self, ctx: commands.Context, member: discord.Member = None):
        await self._send_profil(ctx.channel, ctx.author, ctx.guild, member)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ProfilCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Profil"
    await bot.add_cog(cog)
