# ────────────────────────────────────────────────────────────────────────────────
# 📌 botinfo.py
# Objectif : Afficher toutes les informations utiles et stats du bot dans un seul embed
# Catégorie : Admin
# Accès : Admin
# Cooldown : 1 / 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import psutil
from datetime import datetime

from utils.discord_utils import safe_send, safe_edit  

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class BotInfo(commands.Cog):
    """
    Commande /botinfo et !botinfo — Affiche toutes les infos utiles du bot dans un embed
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Préparation de l'embed avec toutes les infos
    # ────────────────────────────────────────────────────────────────────────────
    def get_bot_embed(self) -> discord.Embed:
        # Uptime
        delta = datetime.utcnow() - self.start_time
        uptime = str(delta).split(".")[0]

        # Serveurs et membres
        total_members = sum(g.member_count for g in self.bot.guilds)
        total_guilds = len(self.bot.guilds)

        # Ping
        latency = round(self.bot.latency * 1000)

        # Cogs et commandes
        cogs = list(self.bot.cogs.keys())
        commands_list = [c.name for c in self.bot.commands if not getattr(c, "hidden", False)]

        # CPU / Mémoire
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024
        cpu = psutil.cpu_percent(interval=0.1)

        # Création de l'embed
        embed = discord.Embed(
            title=f"🤖 Informations du bot — {self.bot.user.name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="Nom", value=self.bot.user.name, inline=True)
        embed.add_field(name="ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.add_field(name="Ping", value=f"{latency} ms", inline=True)
        embed.add_field(name="Serveurs", value=total_guilds, inline=True)
        embed.add_field(name="Membres totaux", value=total_members, inline=True)
        embed.add_field(name="Mémoire utilisée", value=f"{mem:.2f} MB", inline=True)
        embed.add_field(name="CPU utilisé", value=f"{cpu} %", inline=True)
        embed.add_field(name="Cogs chargés", value=", ".join(cogs) if cogs else "Aucun", inline=False)
        embed.add_field(name="Commandes disponibles", value=", ".join(commands_list) if commands_list else "Aucune", inline=False)

        embed.set_footer(text="Bot Admin Info")
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="botinfo",
        description="Affiche toutes les infos utiles et stats du bot (admin)."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_botinfo(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = self.get_bot_embed()
        await safe_send(interaction.channel, embed=embed)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="botinfo")
    @commands.has_permissions(administrator=True)
    async def prefix_botinfo(self, ctx: commands.Context):
        embed = self.get_bot_embed()
        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = BotInfo(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
