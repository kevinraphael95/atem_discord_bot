# ────────────────────────────────────────────────────────────────────────────────
# 📌 classement.py — Commande interactive !classement
# Objectif :
#   - Afficher le classement paginé du tournoi depuis Google Sheets
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 5 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import csv
import io
import os

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination interactive
# ────────────────────────────────────────────────────────────────────────────────
class ClassementView(View):
    def __init__(self, bot, classement: list[tuple], user_id: int, page: int = 0, page_size: int = 10, parent=None):
        super().__init__(timeout=120)
        self.bot = bot
        self.classement = classement
        self.user_id = user_id
        self.page = page
        self.page_size = page_size
        self.parent = parent  # référence vers le Cog
        self.message = None

        self.prev_button.disabled = (self.page == 0)
        self.next_button.disabled = (self.page >= (len(self.classement)-1)//self.page_size)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
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

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Classement(commands.Cog):
    """Commande /classement et !classement — Affiche le classement du tournoi depuis Google Sheets."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sheet_csv_url = os.getenv("VAACT_CLASSEMENT_SHEET")

    async def fetch_csv(self):
        async with aiohttp.ClientSession() as session:
            resp = await session.get(self.sheet_csv_url)
            if resp.status != 200:
                return None
            text = await resp.text()
            return list(csv.reader(io.StringIO(text)))

    def create_embed(self, classement, page, page_size=10):
        total_pages = (len(classement) - 1) // page_size + 1
        embed = discord.Embed(
            title=f"🏆 Classement VAACT — Page {page+1}/{total_pages}",
            color=discord.Color.gold()
        )
        medals = ["🥇", "🥈", "🥉"]
        start = page * page_size
        end = start + page_size
        lignes = []
        for i, (joueur, pts) in enumerate(classement[start:end], start=start):
            prefix = medals[i] if i < 3 else f"{i+1}ᵉ"
            lignes.append(f"**{prefix}** {joueur} — {pts} pts")
        embed.add_field(name="Joueurs", value="\n".join(lignes), inline=False)
        return embed

    async def _show_classement(self, channel, user_id):
        rows = await self.fetch_csv()
        if not rows or len(rows) < 3:
            await safe_send(channel, "❌ Impossible de récupérer le classement.")
            return

        classement = []
        for row in rows[2:]:  # on saute les 2 premières lignes
            if len(row) < 6 or not row[2].strip():
                break
            joueur = row[2].strip()
            pts = row[5].strip() or "0"
            classement.append((joueur, pts))

        if not classement:
            await safe_send(channel, "❌ Aucun joueur trouvé dans le classement.")
            return

        page_size = 10
        view = ClassementView(self.bot, classement, user_id, page=0, page_size=page_size, parent=self)
        embed = self.create_embed(classement, 0, page_size)
        view.message = await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="classement",
        description="Affiche le classement du tournoi avec pagination interactive."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_classement(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._show_classement(interaction.channel, interaction.user.id)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="classement",
        help="🏆 Affiche le classement du tournoi avec pagination interactive."
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_classement(self, ctx: commands.Context):
        await self._show_classement(ctx.channel, ctx.author.id)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Classement(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
