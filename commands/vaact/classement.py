# ────────────────────────────────────────────────────────────────────────────────
# 📌 classement.py — Commande interactive !classement
# Objectif : Afficher le classement du tournoi à partir du Google Sheets
# Catégorie : Yu-Gi-Oh
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
        # Export CSV public du Google Sheets
        self.sheet_csv_url = "https://docs.google.com/spreadsheets/d/15xP7G1F_oty5pn2nOVG2GwtiEZoccKB_oA7-2nT44l8/export?format=csv"

    async def fetch_csv(self):
        async with aiohttp.ClientSession() as session:
            resp = await session.get(self.sheet_csv_url)
            if resp.status != 200:
                return None
            text = await resp.text()
            return list(csv.reader(io.StringIO(text)))

    @commands.command(
        name="classement",
        help="Affiche le classement du tournoi en cours.",
        description="Récupère le classement depuis Google Sheets et l’affiche joliment."
    )
    async def classement(self, ctx: commands.Context):
        try:
            rows = await self.fetch_csv()
            if not rows or len(rows) < 2:
                await safe_send(ctx.channel, "❌ Impossible de récupérer ou le classement est vide.")
                return

            # En-têtes + données
            headers = rows[0]
            data = rows[1:10]  # Top 10

            lines = []
            for i, row in enumerate(data):
                nom = row[1].strip()
                if i == 0:
                    lines.append(f"🥇 {nom}")
                elif i == 1:
                    lines.append(f"🥈 {nom}")
                elif i == 2:
                    lines.append(f"🥉 {nom}")
                else:
                    lines.append(f"{i+1} - {nom}")

            embed = discord.Embed(
                title="🏆 Classement VAACT",
                description="\n".join(lines),
                color=discord.Color.purple()
            )

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
