# ────────────────────────────────────────────────────────────────────────────────
# 📌 cartefav.py — Commande interactive !cartefav
# Objectif : Afficher les cartes favorites d’un utilisateur Discord
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from utils.discord_utils import safe_send  # ✅ Utilisation des safe_

from supabase_client import supabase  # Client Supabase déjà configuré

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CarteFav(commands.Cog):
    """
    Commande !cartefav — Affiche les cartes favorites d’un utilisateur Discord.
    Usage : !cartefav [@utilisateur]
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="cartefav",
        help="⭐ Affiche les cartes favorites de l’utilisateur mentionné ou de vous-même.",
        description="Affiche la liste des cartes favorites stockées pour un utilisateur."
    )
    async def cartefav(self, ctx: commands.Context, user: discord.User = None):
        """Affiche les cartes favorites d’un utilisateur Discord"""
        user = user or ctx.author
        user_id = str(user.id)

        try:
            response = supabase.table("favorites").select("cartefav").eq("user_id", user_id).execute()
            if response.status_code != 200:
                return await safe_send(ctx.channel, "❌ Erreur lors de la récupération des cartes favorites.")

            cartes = [entry["cartefav"] for entry in response.data]

            if not cartes:
                if user == ctx.author:
                    await safe_send(ctx.channel, "❌ Vous n’avez pas encore de carte favorite.")
                else:
                    await safe_send(ctx.channel, f"❌ {user.display_name} n’a pas encore de carte favorite.")
                return

            cartes_str = "\n".join(f"• {c}" for c in cartes)
            embed = discord.Embed(
                title=f"⭐ Cartes favorites de {user.display_name}",
                description=cartes_str,
                color=discord.Color.gold()
            )
            await safe_send(ctx.channel, embed=embed)

        except Exception as e:
            print(f"[ERREUR cartefav] {e}")
            await safe_send(ctx.channel, "🚨 Une erreur est survenue lors de la récupération des cartes favorites.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CarteFav(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
