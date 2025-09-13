# ────────────────────────────────────────────────────────────────────────────────
# 📌 profil.py — Commande pour afficher le profil VAACT d’un utilisateur
# Objectif : Affiche les informations enregistrées dans la table "profil"
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
from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_respond
import json

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ProfilCommand(commands.Cog):
    """Commande /profil et !profil — Affiche le profil complet d’un utilisateur"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # Fonction interne pour envoyer le profil
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_profil(self, ctx_or_interaction, author, guild, target_user):
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
        if not profil_data.data:
            return await safe_respond(ctx_or_interaction, f"❌ Aucun profil trouvé pour {user.display_name}.", ephemeral=True)

        profil = profil_data.data[0]
        cartefav = profil.get("cartefav", "Aucune")
        vaact_name = profil.get("vaact_name", "Non défini")
        fav_decks = profil.get("fav_decks_vaact", [])
        decks_text = ", ".join(fav_decks) if fav_decks else "Aucun"

        # 🔹 Construction de l'embed
        embed = discord.Embed(
            title=f"__**Profil de {user.display_name}**__",
            description=(
                f"**Carte préférée** : {cartefav}\n"
                f"**Pseudo VAACT** : {vaact_name}\n"
                f"**Decks VAACT préférés** : {decks_text}"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Utilisateur : {user.name} ({user.id})")

        # 🔹 Envoi selon le contexte
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await safe_send(ctx_or_interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # Commande SLASH /profil
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="profil", description="📋 Affiche le profil d’un membre")
    @app_commands.describe(member="Membre dont vous voulez voir le profil")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_profil(self, interaction: discord.Interaction, member: discord.Member = None):
        try:
            await self._send_profil(interaction, interaction.user, interaction.guild, member)
        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /profil] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # Commande PREFIX !profil
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
