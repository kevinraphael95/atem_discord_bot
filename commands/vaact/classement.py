# ────────────────────────────────────────────────────────────────────────────────
# 📌 classement.py — Commande interactive !classement
# Objectif : Afficher le classement du tournoi à partir du Google Sheets
# Catégorie : 🃏 Yu-Gi-Oh
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
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Classement(commands.Cog):
    """
    Commande !classement — Montre le classement actuel du tournoi depuis Google Sheets.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # URL d’export CSV public du premier onglet
        self.sheet_csv_url = (
            "https://docs.google.com/spreadsheets/"
            "d/15xP7G1F_oty5pn2nOVG2GwtiEZoccKB_oA7-2nT44l8/export?"
            "format=csv&gid=2118626088"
        )

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
                await safe_send(ctx.channel, "❌ Impossible de récupérer le classement.")
                return

            classement = []
            for row in rows[1:]:  # saute l’en-tête
                # arrêt si ligne vide ou nom vide en colonne 3 (index 2)
                if len(row) < 3 or not row[2].strip():
                    break
                joueur = row[2].strip()
                pts = row[3].strip() if len(row) > 3 and row[3].strip() else "0"
                classement.append((joueur, pts))

            if not classement:
                await safe_send(ctx.channel, "❌ Aucun joueur trouvé dans le classement.")
                return

            embed = discord.Embed(
                title="🏆 Classement VAACT",
                color=discord.Color.gold()
            )
            medals = ["🥇", "🥈", "🥉"]

            for i, (joueur, pts) in enumerate(classement[:10]):
                prefix = medals[i] if i < 3 else f"{i+1} -"
                embed.add_field(
                    name=f"{prefix} {joueur}",
                    value=f"{pts} pts",
                    inline=False
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
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
