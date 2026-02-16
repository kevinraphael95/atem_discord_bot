# ────────────────────────────────────────────────────────────────────────────────
# 📌 sets.py
# Objectif : Afficher tous les sets d’une carte Yu-Gi-Oh! avec pagination interactive
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes par utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.card_utils import search_card

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Pagination interactive des sets
# ────────────────────────────────────────────────────────────────────────────────
class SetsPagination(View):
    """Navigation interactive entre les sets d’une carte."""

    def __init__(self, sets: list[dict], card_name: str):
        super().__init__(timeout=120)
        self.sets = sets
        self.index = 0
        self.card_name = card_name
        self.message = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

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
# 🧠 Cog principal avec cooldown centralisé
# ────────────────────────────────────────────────────────────────────────────────
class Sets(commands.Cog):
    """
    Commande /sets et !sets — Affiche tous les sets d’une carte Yu-Gi-Oh!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_sets(self, channel: discord.abc.Messageable, nom: str):
        carte, langue, message = await search_card(nom, self.bot.aiohttp_session)

        if message:
            await safe_send(channel, message)
            return

        if not carte:
            await safe_send(channel, f"❌ Impossible de trouver la carte `{nom}`.")
            return

        sets = carte.get("card_sets", [])
        if not sets:
            await safe_send(channel, "❌ Aucun set disponible pour cette carte.")
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

        view = SetsPagination(sets, carte.get("name"))
        view.message = await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="sets",
        description="📦 Affiche tous les sets d’une carte avec rareté, prix et date TCG."
    )
    @app_commands.describe(nom="Nom de la carte")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_sets(self, interaction: discord.Interaction, nom: str):
        await interaction.response.defer()
        await self._send_sets(interaction.channel, nom)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="sets")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_sets(self, ctx: commands.Context, *, nom: str):
        await self._send_sets(ctx.channel, nom)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Sets(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
