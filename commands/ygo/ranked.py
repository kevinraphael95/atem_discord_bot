# ────────────────────────────────────────────────────────────────────────────────
# 📌 ranked.py
# Objectif : Gestion des commandes Ranked (score ELO, stats et classement Top 10)
# Catégorie : Yu-Gi-Oh
# Accès : Tous
# Cooldown : 5.0s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os

from utils.discord_utils import safe_send
from utils.elo_db import get_or_create_player, ATEM_ELO_DB

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec cooldowns centralisés
# ────────────────────────────────────────────────────────────────────────────────
class Ranked(commands.Cog):
    """
    Commande /rank, !rank, /leaderboard et !leaderboard — Système Ranked VAACT
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonctions internes communes
    # ────────────────────────────────────────────────────────────────────────────
    async def _show_rank(self, channel: discord.abc.Messageable, author_name: str, target_name: str = None):
        target = target_name if target_name else author_name
        elo, wins, losses = get_or_create_player(target)
        total = wins + losses
        ratio = round((wins / total * 100), 1) if total > 0 else 0

        embed = discord.Embed(
            title=f"🔮 Profil Duelliste — {target}",
            color=discord.Color.red()
        )
        embed.add_field(name="Score ELO", value=f"**{elo}**", inline=True)
        embed.add_field(name="Stats", value=f"{wins}V / {losses}D", inline=True)
        embed.add_field(name="Winrate", value=f"{ratio}%", inline=True)
        embed.set_footer(text="Atem Ranked System")

        await safe_send(channel, embed=embed)

    async def _show_leaderboard(self, channel: discord.abc.Messageable):
        if not os.path.exists(ATEM_ELO_DB):
            await safe_send(channel, "❌ Aucune donnée ELO enregistrée pour le moment.")
            return

        conn = sqlite3.connect(ATEM_ELO_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT username, elo, wins, losses FROM players ORDER BY elo DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()

        embed = discord.Embed(
            title="🏆 Top 10 Duellistes VAACT",
            color=discord.Color.gold()
        )
        desc = ""
        for idx, (user, elo, w, l) in enumerate(rows, 1):
            desc += f"**#{idx} {user}** — {elo} ELO *({w}V / {l}D)*\n"

        embed.description = desc if desc else "Aucun duel enregistré pour le moment."
        await safe_send(channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH — Rank
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="rank",
        description="Affiche le classement ELO et le profil d'un duelliste."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_rank(self, interaction: discord.Interaction, joueur: str = None):
        await interaction.response.defer()
        await self._show_rank(interaction.channel, interaction.user.name, joueur)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX — Rank
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="rank")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_rank(self, ctx: commands.Context, joueur: str = None):
        await self._show_rank(ctx.channel, ctx.author.name, joueur)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH — Leaderboard
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="leaderboard",
        description="Affiche le Top 10 des duellistes du serveur."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._show_leaderboard(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX — Leaderboard
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="leaderboard")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_leaderboard(self, ctx: commands.Context):
        await self._show_leaderboard(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Ranked(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
