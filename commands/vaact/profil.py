# ────────────────────────────────────────────────────────────────────────────────
# 📌 profil.py — Affiche le profil d’un utilisateur
# Objectif : Voir son profil ou celui d’un membre
# Catégorie : Autre
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
        profil_data = await self.get_profil(membre.id, membre.name)
        embed = self.build_embed(profil_data, membre)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="profil", aliases=["p"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_profil(self, ctx: commands.Context, membre: discord.Member = None):
        membre = membre or ctx.author
        profil_data = await self.get_profil(membre.id, membre.name)
        embed = self.build_embed(profil_data, membre)
        await safe_send(ctx.channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Récupération du profil depuis Supabase (infos + stats depuis ygo_streaks)
    # ────────────────────────────────────────────────────────────────────────────
    async def get_profil(self, user_id: int, username: str) -> dict:
        profil = {
            "user_id": str(user_id),
            "username": username,
            "cartefav": "Non défini",
            "vaact_name": "Non défini",
            "fav_decks_vaact": "Non défini",
            "current_streak": 0,
            "best_streak": 0,
            "illu_streak": 0,
            "best_illustreak": 0
        }

        try:
            # Récupération infos perso depuis table 'profil'
            resp_profil = self.bot.supabase.table("profil").select("*").eq("user_id", str(user_id)).execute()
            if resp_profil.data and len(resp_profil.data) > 0:
                profil.update(resp_profil.data[0])
            else:
                # Création profil par défaut si inexistant
                self.bot.supabase.table("profil").insert({
                    "user_id": str(user_id),
                    "username": username
                }).execute()

            # Récupération stats depuis table 'ygo_streaks'
            resp_stats = self.bot.supabase.table("ygo_streaks").select("*").eq("user_id", str(user_id)).execute()
            if resp_stats.data and len(resp_stats.data) > 0:
                stats = resp_stats.data[0]
                profil["current_streak"] = stats.get("current_streak", 0)
                profil["best_streak"] = stats.get("best_streak", 0)
                profil["illu_streak"] = stats.get("illu_streak", 0)
                profil["best_illustreak"] = stats.get("best_illustreak", 0)
            else:
                # Crée stats par défaut si inexistantes
                self.bot.supabase.table("ygo_streaks").insert({
                    "user_id": str(user_id),
                    "current_streak": 0,
                    "best_streak": 0,
                    "illu_streak": 0,
                    "best_illustreak": 0
                }).execute()

            return profil

        except Exception as e:
            print(f"[Supabase] Impossible de récupérer le profil : {e}")
            return profil

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
            f"Carte Yu-Gi-Oh préférée : {profil.get('cartefav', 'Non défini')}\n"
            f"Pseudo VAACT : {profil.get('vaact_name', 'Non défini')}\n"
            f"Deck VAACT préféré : {profil.get('fav_decks_vaact', 'Non défini')}"
        )
        embed.add_field(name="Infos", value=contenu, inline=False)
        
        # Champ Stats
        stats = (
            f"Série actuelle de "Devine la Description" : {profil.get('current_streak', 0)}\n"
            f"Meilleure série de "Devine la Description" : {profil.get('best_streak', 0)}\n"
            f"Série actuelle de "Devine l’illustration" : {profil.get('illu_streak', 0)}\n"
            f"Meilleure série de "Devine l’illustration" : {profil.get('best_illustreak', 0)}"
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
