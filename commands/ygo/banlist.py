# ────────────────────────────────────────────────────────────────────────────────
# 📌 banlist.py — Commande simple /banlist et !banlist
# Objectif : Affiche les cartes d'une banlist (TCG, OCG, GOAT)
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
import aiohttp
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Banlist(commands.Cog):
    """
    Commande /banlist et !banlist — Affiche les cartes d'une banlist (TCG, OCG, GOAT)
    """
    BASE_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Méthode interne pour récupérer les cartes
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_banlist(self, banlist_type: str):
        """Récupère les cartes selon la banlist choisie"""
        params = {"banlist": banlist_type, "sort": "name"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("data", [])

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="banlist",
        description="Affiche les cartes d'une banlist (tcg, ocg ou goat)."
    )
    @app_commands.describe(banlist="Type de banlist: tcg, ocg, goat")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_banlist(self, interaction: discord.Interaction, banlist: str):
        """Commande slash pour afficher la banlist"""
        await safe_respond(interaction, f"🔄 Récupération de la banlist **{banlist.upper()}**…")
        banlist_type = banlist.lower()
        if banlist_type not in ("tcg", "ocg", "goat"):
            return await safe_respond(interaction, "❌ Type de banlist invalide. Utilise tcg, ocg ou goat.")
        
        cards = await self.fetch_banlist(banlist_type)
        if not cards:
            return await safe_respond(interaction, "❌ Impossible de récupérer les cartes.")

        description = "\n".join(f"**{c['name']}** - {c['type']}" for c in cards[:10])
        embed = discord.Embed(
            title=f"📌 Cartes sur la banlist {banlist.upper()}",
            description=description,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Affichage des 10 premiers sur {len(cards)}")
        await interaction.edit_original_response(embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="banlist")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_banlist(self, ctx: commands.Context, banlist: str):
        """Commande préfixe pour afficher la banlist"""
        msg = await safe_send(ctx.channel, f"🔄 Récupération de la banlist **{banlist.upper()}**…")
        banlist_type = banlist.lower()
        if banlist_type not in ("tcg", "ocg", "goat"):
            return await safe_send(ctx.channel, "❌ Type de banlist invalide. Utilise tcg, ocg ou goat.")
        
        cards = await self.fetch_banlist(banlist_type)
        if not cards:
            return await safe_send(ctx.channel, "❌ Impossible de récupérer les cartes.")

        description = "\n".join(f"**{c['name']}** - {c['type']}" for c in cards[:10])
        embed = discord.Embed(
            title=f"📌 Cartes sur la banlist {banlist.upper()}",
            description=description,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Affichage des 10 premiers sur {len(cards)}")
        await msg.edit(content=None, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Banlist(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Autre"
    await bot.add_cog(cog)
