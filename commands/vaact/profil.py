# ────────────────────────────────────────────────────────────────────────────────
# 📌 profil.py — Affiche le profil d’un utilisateur
# Objectif : Voir son profil ou celui d’un membre
# Catégorie : VAACT
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond
from utils.vaact_utils import get_or_create_profile

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Profil(commands.Cog):
    """Commande /profil et !profil — Voir son profil ou celui d’un membre"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="profil",
        description="Affiche le profil d’un utilisateur."
    )
    @app_commands.describe(membre="Le membre dont vous voulez voir le profil")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_profil(self, interaction: discord.Interaction, membre: discord.Member = None):
        membre = membre or interaction.user
        profil_data = await get_or_create_profile(membre.id, membre.name)
        embed = self.build_embed(profil_data, membre)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="profil", aliases=["p"], help="Affiche le profil d’un utilisateur.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_profil(self, ctx: commands.Context, membre: discord.Member = None):
        membre = membre or ctx.author
        profil_data = await get_or_create_profile(membre.id, membre.name)
        embed = self.build_embed(profil_data, membre)
        await safe_send(ctx.channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Création de l’embed
    # ────────────────────────────────────────────────────────────────────────────
    def build_embed(self, profil: dict, membre: discord.Member) -> discord.Embed:
        embed = discord.Embed(
            title=f"Profil de {membre.display_name}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=membre.display_avatar.url)
    
        # Champ Infos
        contenu = (
            f"• Carte Yu-Gi-Oh préférée : {profil.get('cartefav', 'Non défini')}\n"
            f"• Pseudo VAACT : {profil.get('vaact_name', 'Non défini')}\n"
            f"• Deck VAACT préféré : {profil.get('fav_decks_vaact', 'Non défini')}"
        )
        embed.add_field(name="Infos", value=contenu, inline=False)
        
        # Champ Stats avec XP affichée 0/5 max
        niveau = profil.get("niveau", 1)
        exp = profil.get("exp", 0)
        stats = (
            f"• Niveau : {niveau} (XP : {exp}/5)\n"
            f"• ''Devine la Description'' : Série en cours : {profil.get('current_streak', 0)} / Série record : {profil.get('best_streak', 0)}\n"
            f"• ''Devine l’illustration'' : Série en cours : {profil.get('illu_streak', 0)} / Série record : {profil.get('best_illustreak', 0)}"
        )
        embed.add_field(name="Stats", value=stats, inline=False)
        
        return embed


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Profil(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
