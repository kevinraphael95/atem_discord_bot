# ────────────────────────────────────────────────────────────────────────────────
# 📌 setsrecents.py
# Objectif : Afficher automatiquement les sets Yu-Gi-Oh! récents
# Catégorie : Informations
# Accès : Tous
# Cooldown : 1 / 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select
import json
import os
import aiohttp
from datetime import datetime

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_delete  

# ────────────────────────────────────────────────────────────────────────────────
# 📂 JSON cache
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "setsrecents.json")
YGOPRO_SETS_API = "https://db.ygoprodeck.com/api/v7/cardsets.php"
YGOPRO_CARDS_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Chargement / génération auto des données
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_json(url, params=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as r:
            return await r.json()

async def generate_sets_json(limit=10):
    sets_data = await fetch_json(YGOPRO_SETS_API)

    tcg_sets = [s for s in sets_data if s.get("tcg_date")]
    tcg_sets.sort(
        key=lambda s: datetime.strptime(s["tcg_date"], "%Y-%m-%d"),
        reverse=True
    )

    result = {}

    for s in tcg_sets[:limit]:
        cards_data = await fetch_json(
            YGOPRO_CARDS_API,
            params={"cardset": s["set_name"]}
        )
        cards = [c["name"] for c in cards_data.get("data", [])]

        result[s["set_name"]] = {
            "date": s["tcg_date"],
            "cards": cards
        }

    os.makedirs("data", exist_ok=True)
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result

async def load_data():
    if os.path.exists(DATA_JSON_PATH):
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    return await generate_sets_json()

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Premier menu (sets)
# ────────────────────────────────────────────────────────────────────────────────
class FirstSelectView(View):
    def __init__(self, bot, data):
        super().__init__(timeout=120)
        self.bot = bot
        self.data = data
        self.message = None
        self.add_item(FirstSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class FirstSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=name,
                description=f"Date TCG : {infos['date']}"
            )
            for name, infos in self.parent_view.data.items()
        ]
        super().__init__(
            placeholder="📦 Choisis un set récent",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        set_name = self.values[0]
        new_view = SecondSelectView(
            self.parent_view.bot,
            self.parent_view.data,
            set_name
        )
        new_view.message = interaction.message

        await safe_edit(
            interaction.message,
            content=f"📘 **{set_name}** sélectionné\nChoisis une carte :",
            embed=None,
            view=new_view
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Deuxième menu (cartes)
# ────────────────────────────────────────────────────────────────────────────────
class SecondSelectView(View):
    def __init__(self, bot, data, key):
        super().__init__(timeout=120)
        self.bot = bot
        self.data = data
        self.key = key
        self.message = None
        self.add_item(SecondSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class SecondSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        cards = self.parent_view.data[self.parent_view.key]["cards"][:25]

        options = [discord.SelectOption(label=card) for card in cards]
        super().__init__(
            placeholder="🃏 Choisis une carte",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🃏 Carte sélectionnée",
            color=discord.Color.gold()
        )
        embed.add_field(name="Set", value=self.parent_view.key, inline=False)
        embed.add_field(name="Carte", value=self.values[0], inline=False)

        await safe_edit(
            interaction.message,
            content=None,
            embed=embed,
            view=None
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class SetsRecents(commands.Cog):
    """Commande /setsrecents et !setsrecents"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_menu(self, channel):
        data = await load_data()
        view = FirstSelectView(self.bot, data)
        view.message = await safe_send(
            channel,
            "📦 Sélectionne un set Yu-Gi-Oh! récent :",
            view=view
        )

    @app_commands.command(
        name="setsrecents",
        description="Affiche automatiquement les sets Yu-Gi-Oh! récents."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_setsrecents(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_menu(interaction.channel)
        await interaction.delete_original_response()

    @commands.command(name="setsrecents", aliases=["setsrec"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_setsrecents(self, ctx: commands.Context):
        await self._send_menu(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = SetsRecents(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
