# ────────────────────────────────────────────────────────────────────────────────
# 📌 classement.py — Commande interactive !classement
# Objectif : Afficher le classement paginé du tournoi depuis Google Sheets
# Catégorie : 🃏 Yu-Gi-Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import csv
import io
from utils.discord_utils import safe_send, safe_edit  # ✅ Utilisation des safe_

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Classement(commands.Cog):
    """
    Commande !classement — Affiche le classement paginé du tournoi depuis Google Sheets.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
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

    def create_embed(self, classement, page, page_size=10):
        embed = discord.Embed(
            title=f"🏆 Classement VAACT — Page {page+1}/{(len(classement)-1)//page_size + 1}",
            color=discord.Color.gold()
        )
        medals = ["🥇", "🥈", "🥉"]

        start = page * page_size
        end = start + page_size
        for i, (joueur, pts) in enumerate(classement[start:end], start=start):
            prefix = medals[i] if i < 3 else f"{i+1} -"
            embed.add_field(
                name=f"{prefix} {joueur}",
                value=f"({pts} pts)",
                inline=False
            )
        return embed

    @commands.command(
        name="classement",
        help="Affiche le classement du tournoi en cours avec pagination.",
        description="Récupère le classement depuis Google Sheets et l’affiche par pages."
    )
    async def classement(self, ctx: commands.Context):
        try:
            rows = await self.fetch_csv()
            if not rows or len(rows) < 3:
                await safe_send(ctx.channel, "❌ Impossible de récupérer le classement.")
                return

            classement = []
            for row in rows[2:]:  # On saute les 2 premières lignes
                if len(row) < 6 or not row[2].strip():
                    break
                joueur = row[2].strip()        # Nom en colonne 3 (index 2)
                pts = row[5].strip() or "0"   # Points en colonne 6 (index 5)
                classement.append((joueur, pts))

            if not classement:
                await safe_send(ctx.channel, "❌ Aucun joueur trouvé dans le classement.")
                return

            page = 0
            page_size = 10
            embed = self.create_embed(classement, page, page_size)

            class PaginationView(View):
                def __init__(self, bot, classement, user_id, page=0, page_size=10):
                    super().__init__(timeout=120)
                    self.bot = bot
                    self.classement = classement
                    self.page = page
                    self.page_size = page_size
                    self.user_id = user_id  # ID de l’utilisateur autorisé
                    self.prev_button.disabled = (self.page == 0)
                    self.next_button.disabled = (self.page >= (len(self.classement)-1)//self.page_size)

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    # Seul l'utilisateur qui a lancé la commande peut interagir
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message(
                            "❌ Tu n'es pas autorisé à utiliser ces boutons.",
                            ephemeral=True
                        )
                        return False
                    return True

                @discord.ui.button(label="⬅ Précédent", style=discord.ButtonStyle.primary)
                async def prev_button(self, interaction: discord.Interaction, button: Button):
                    if self.page > 0:
                        self.page -= 1
                        embed = self.parent.create_embed(self.classement, self.page, self.page_size)
                        self.prev_button.disabled = (self.page == 0)
                        self.next_button.disabled = False
                        await safe_edit(interaction.message, embed=embed, view=self)

                @discord.ui.button(label="Suivant ➡", style=discord.ButtonStyle.primary)
                async def next_button(self, interaction: discord.Interaction, button: Button):
                    max_page = (len(self.classement) - 1) // self.page_size
                    if self.page < max_page:
                        self.page += 1
                        embed = self.parent.create_embed(self.classement, self.page, self.page_size)
                        self.next_button.disabled = (self.page == max_page)
                        self.prev_button.disabled = False
                        await safe_edit(interaction.message, embed=embed, view=self)

            PaginationView.parent = self

            view = PaginationView(self.bot, classement, ctx.author.id, page, page_size)
            await safe_send(ctx.channel, embed=embed, view=view)

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
            command.category = "🃏 Yu-Gi-Oh"
    await bot.add_cog(cog)
