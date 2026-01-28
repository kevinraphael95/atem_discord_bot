# ────────────────────────────────────────────────────────────────────────────────
# 📌 setsrecents.py
# Objectif : Afficher les derniers sets Yu-Gi-Oh! et leurs cartes avec rareté/prix
# Catégorie : Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select
import requests

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des sets Yu-Gi-Oh! via API
# ────────────────────────────────────────────────────────────────────────────────
def load_sets():
    """Récupère la liste des sets récents via l'API YGOPRODeck"""
    try:
        r = requests.get("https://db.ygoprodeck.com/api/v7/cardsets.php")
        return sorted(r.json(), key=lambda x: x["tcg_date"], reverse=True)
    except Exception as e:
        print(f"[ERREUR API] Impossible de récupérer les sets : {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Premier menu interactif
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
    def __init__(self, parent_view: FirstSelectView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=s["set_name"][:100],
                description=f'{s["tcg_date"]} • {s["num_of_cards"]} cartes',
                value=s["set_name"]
            ) for s in self.parent_view.data[:25]
        ]
        super().__init__(placeholder="Sélectionne un set récent", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_key = self.values[0]
        new_view = SecondSelectView(self.parent_view.bot, selected_key)
        new_view.message = interaction.message
        await safe_edit(
            interaction.message,
            content=f"Set sélectionné : **{selected_key}**\nVoici toutes les cartes :",
            embed=None,
            view=new_view
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Deuxième menu interactif
# ────────────────────────────────────────────────────────────────────────────────
class SecondSelectView(View):
    def __init__(self, bot, set_name):
        super().__init__(timeout=120)
        self.bot = bot
        self.set_name = set_name
        self.message = None
        self.add_item(SecondSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class SecondSelect(Select):
    def __init__(self, parent_view: SecondSelectView):
        self.parent_view = parent_view
        # Récupère les cartes du set
        try:
            r = requests.get("https://db.ygoprodeck.com/api/v7/cardinfo.php", params={"cardset": parent_view.set_name, "language": "fr"})
            self.cards = r.json().get("data", [])
        except Exception as e:
            print(f"[ERREUR API] Impossible de récupérer les cartes : {e}")
            self.cards = []

        options = [
            discord.SelectOption(label=card["name"][:100], value=card["id"])
            for card in self.cards[:25]
        ]
        super().__init__(placeholder="Sélectionne une carte pour détails", options=options)

    async def callback(self, interaction: discord.Interaction):
        card_id = int(self.values[0])
        card = next((c for c in self.cards if c["id"] == card_id), None)
        if not card:
            return await safe_edit(interaction.message, content="❌ Carte introuvable.", view=None)

        embed = discord.Embed(
            title=f"{card['name']} ({self.parent_view.set_name})",
            color=discord.Color.blue()
        )
        if "card_sets" in card:
            for s in card["card_sets"]:
                if s["set_name"] == self.parent_view.set_name:
                    embed.add_field(
                        name=s["set_rarity"],
                        value=f"💰 {s['set_price']}$",
                        inline=False
                    )
        if "card_images" in card and card["card_images"]:
            embed.set_thumbnail(url=card["card_images"][0]["image_url"])

        await safe_edit(
            interaction.message,
            content=None,
            embed=embed,
            view=None
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec cooldowns centralisés
# ────────────────────────────────────────────────────────────────────────────────
class SetsRecents(commands.Cog):
    """
    Commande /setsrecents et !setsrecents — Voir les derniers sets Yu-Gi-Oh! et leurs cartes
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_menu(self, channel: discord.abc.Messageable):
        data = load_sets()
        if not data:
            await safe_send(channel, "❌ Impossible de récupérer les sets.")
            return
        view = FirstSelectView(self.bot, data)
        view.message = await safe_send(channel, "📦 Choisis un set récent :", view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="setsrecents",
        description="Affiche les derniers sets Yu-Gi-Oh!"
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
            command.category = "Yu-Gi-Oh!"
    await bot.add_cog(cog)
