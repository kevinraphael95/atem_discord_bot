# ────────────────────────────────────────────────────────────────────────────────
# 📌 sets.py — Commande interactive !sets
# Objectif :
#   - Afficher tous les sets d’une carte Yu-Gi-Oh!
#   - Navigation interactive entre les sets
#   - Utilise utils/card_utils pour toutes les requêtes API
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send
from utils.card_utils import search_card

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination interactive des sets
# ────────────────────────────────────────────────────────────────────────────────
class SetsPagination(View):
    """Navigation interactive entre les sets d’une carte."""

    def __init__(self, sets: list[dict], card_name: str):
        super().__init__(timeout=120)
        self.sets = sets
        self.index = 0
        self.card_name = card_name

    async def update_embed(self, interaction: discord.Interaction):
        s = self.sets[self.index]
        prix_cm = s.get("set_price", "N/A")
        rarity = s.get("set_rarity", "N/A")
        date = s.get("tcg_date", "Inconnue")

        embed = discord.Embed(
            title=f"{self.card_name} — Set {self.index + 1}/{len(self.sets)}",
            color=discord.Color.green()
        )
        embed.add_field(
            name=f"{s.get('set_name', 'Set inconnu')} ({s.get('set_code', '')})",
            value=f"Rareté : {rarity}\nPrix : €{prix_cm}\nDate TCG : {date}",
            inline=False
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.sets)
        await self.update_embed(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(self.sets)
        await self.update_embed(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Sets(commands.Cog):
    """Commande !sets — Affiche tous les sets d’une carte Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="sets",
        help="📦 Affiche tous les sets d’une carte avec rareté, prix et date TCG."
    )
    async def sets(self, ctx: commands.Context, *, nom: str):
        carte, langue, message = await search_card(nom, self.bot.aiohttp_session)

        if message:
            await safe_send(ctx, message)
            return
        if not carte:
            await safe_send(ctx, f"❌ Impossible de trouver la carte `{nom}`.")
            return

        sets = carte.get("card_sets", [])
        if not sets:
            await safe_send(ctx, "❌ Aucun set disponible pour cette carte.")
            return

        # Premier embed
        s = sets[0]
        prix_cm = s.get("set_price", "N/A")
        rarity = s.get("set_rarity", "N/A")
        date = s.get("tcg_date", "Inconnue")

        embed = discord.Embed(
            title=f"{carte.get('name', 'Carte inconnue')} — Set 1/{len(sets)}",
            color=discord.Color.green()
        )
        embed.add_field(
            name=f"{s.get('set_name', 'Set inconnu')} ({s.get('set_code', '')})",
            value=f"Rareté : {rarity}\nPrix : €{prix_cm}\nDate TCG : {date}",
            inline=False
        )

        await safe_send(ctx, embed=embed, view=SetsPagination(sets, carte.get('name')))

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Sets(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
