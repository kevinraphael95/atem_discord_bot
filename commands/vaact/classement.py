# ────────────────────────────────────────────────────────────────────────────────
# 📌 classement.py — Commande interactive !classement
# Objectif : Afficher le classement du tournoi à partir du Google Sheets
# Catégorie : Yu‑Gi‑Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import csv
import io
from utils.discord_utils import safe_send  # ✅ Utilisation des safe_
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Classement(commands.Cog):
    """
    Commande !classement — Montre le classement actuel du tournoi depuis Google Sheets.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Utilise l'ID du bon onglet et l'export CSV (à vérifier sur ton Google Sheet)
        self.sheet_csv_url = "https://docs.google.com/spreadsheets/d/15xP7G1F_oty5pn2nOVG2GwtiEZoccKB_oA7-2nT44l8/export?format=csv&gid=2118626088"

    async def fetch_csv(self):
        async with aiohttp.ClientSession() as session:
            resp = await session.get(self.sheet_csv_url)
            if resp.status != 200:
                return None
            text = await resp.text()
            return list(csv.reader(io.StringIO(text)))

    @commands.command(
        name="classement",
        help="Affiche le classement des tournois VAACT.",
        description="Récupère le classement depuis Google Sheets et l’affiche en embed."
    )
    async def classement(self, ctx: commands.Context):
        try:
            rows = await self.fetch_csv()
            if not rows or len(rows) < 2:
                await safe_send(ctx.channel, "❌ Impossible de récupérer ou classement vide.")
                return

            # Supposons que le sheet ait 3 colonnes : Rang / Joueur / Points
            # et commence dès la première ligne.
            # Adapte si tes colonnes diffèrent ou si l’ordre est différent.

            # On prend tout le classement
            data = rows[1:]  # exclut l’en-tête

            # Embed avec icônes pour les 3 premiers
            embed = discord.Embed(
                title="🏆 Classement du tournoi",
                color=discord.Color.purple()
            )

            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            for i, row in enumerate(data, start=1):
                rank_txt = medals.get(i, f"{i}.")
                name = row[1]
                pts = row[2] if len(row) > 2 else ""
                embed.add_field(name=f"{rank_txt} {name}", value=f"{pts} pts", inline=False)

            await safe_send(ctx.channel, embed=embed)

        except Exception as e:
            print(f"[ERREUR classement] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors de la récupération du classement.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Classement(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
