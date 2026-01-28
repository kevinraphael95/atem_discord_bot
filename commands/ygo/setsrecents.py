# ────────────────────────────────────────────────────────────────────────────────
# 📌 setsrecents.py
# Objectif : Afficher les sets Yu-Gi-Oh! récents et leurs cartes
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select
from datetime import datetime
import requests

from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 API YGOPRODeck
# ────────────────────────────────────────────────────────────────────────────────
API_SETS = "https://db.ygoprodeck.com/api/v7/cardsets.php"
API_CARDS = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Sélection du set
# ────────────────────────────────────────────────────────────────────────────────
class SetsSelectView(View):
    def __init__(self, bot, sets):
        super().__init__(timeout=120)
        self.bot = bot
        self.sets = sets
        self.message = None
        self.add_item(SetsSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)


class SetsSelect(Select):
    def __init__(self, parent_view: SetsSelectView):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(
                label=s["set_name"][:100],
                description=f'{s["tcg_date"]} • {s["num_of_cards"]} cartes',
                value=s["set_name"]
            )
            for s in self.parent_view.sets[:25]
        ]

        super().__init__(
            placeholder="📦 Sélectionne un set récent",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        set_name = self.values[0]
        params = {"cardset": set_name, "language": "fr"}

        r = requests.get(API_CARDS, params=params)
        data = r.json().get("data", [])

        if not data:
            return await safe_respond(interaction, "❌ Aucune carte trouvée.", ephemeral=True)

        embeds = []
        embed = discord.Embed(
            title=f"🃏 {set_name}",
            color=discord.Color.gold()
        )

        count = 0
        for card in data:
            infos = []
            for s in card.get("card_sets", []):
                if s["set_name"] == set_name:
                    infos.append(f"**{s['set_rarity']}** — 💰 `{s['set_price']}$`")

            embed.add_field(
                name=card["name"],
                value="\n".join(infos) if infos else "—",
                inline=False
            )

            count += 1
            if count == 25:
                embeds.append(embed)
                embed = discord.Embed(
                    title=f"🃏 {set_name} (suite)",
                    color=discord.Color.gold()
                )
                count = 0

        embeds.append(embed)

        await safe_edit(
            interaction.message,
            content=None,
            embed=embeds[0],
            view=None
        )

        if len(embeds) > 1:
            for e in embeds[1:]:
                await safe_send(interaction.channel, embed=e)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class SetsRecents(commands.Cog):
    """
    Commande /setsrecents et !setsrecents
    Affiche les sets Yu-Gi-Oh! récents
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_menu(self, channel: discord.abc.Messageable):
        r = requests.get(API_SETS)
        sets = r.json()

        sets_sorted = sorted(
            sets,
            key=lambda x: datetime.strptime(x["tcg_date"], "%Y-%m-%d"),
            reverse=True
        )

        embed = discord.Embed(
            title="📦 Sets Yu-Gi-Oh! récents",
            description="Sélectionne un set pour voir ses cartes, raretés et prix.",
            color=discord.Color.blue()
        )

        view = SetsSelectView(self.bot, sets_sorted)
        view.message = await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="setsrecents",
        description="Affiche les sets Yu-Gi-Oh! récents"
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_setsrecents(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_menu(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="setsrecents")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_setsrecents(self, ctx: commands.Context):
        await self._send_menu(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = SetsRecents(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
