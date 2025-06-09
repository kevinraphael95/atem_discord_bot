# ────────────────────────────────────────────────────────────────────────────────
# 📌 test_csv.py — Commande interactive !testcsv
# Objectif : Vérifie l'accès à un fichier CSV distant (Google Sheets)
# Catégorie : 🧠 VAACT
# Accès : Administrateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import os

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TestCSVCommand(commands.Cog):
    """
    Commande !testcsv — Vérifie l'accès à un fichier CSV distant (Google Sheets)
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sheet_url = os.getenv("SHEET_CSV_URL")

    @commands.command(
        name="testcsv",
        help="🔍 Teste la connexion à un fichier CSV distant (Google Sheets).",
        description="Commande réservée aux administrateurs pour vérifier que le fichier CSV Google Sheets est bien accessible."
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def testcsv(self, ctx: commands.Context):
        """Vérifie si le lien CSV est accessible et affiche un extrait."""

        if not self.sheet_url:
            await ctx.send("❌ URL du CSV introuvable dans les variables d'environnement.")
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.sheet_url) as resp:
                    if resp.status != 200:
                        await ctx.send(
                            f"🚨 Erreur HTTP : {resp.status}\n🔗 URL utilisée :\n{self.sheet_url}"
                        )
                        return

                    data = await resp.text()
                    preview = data[:500]

            await ctx.send(
                f"✅ CSV récupéré avec succès !\n\n```csv\n{preview}\n```"
            )

        except Exception as e:
            await ctx.send(f"❌ Erreur pendant la récupération : `{e}`")

    def cog_load(self):
        self.testcsv.category = "VAACT"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestCSVCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
