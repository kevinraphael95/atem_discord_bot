# ────────────────────────────────────────────────────────────────────────────────
# 📌 devine_carte_buttons.py
# Objectif : Roulette de devinette YGO avec boutons
# Catégorie : Fun
# Accès : Tous
# Cooldown : 5 secondes
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎰 Types disponibles
# ────────────────────────────────────────────────────────────────────────────────
CARD_TYPES = ["monster", "spell", "trap", "token"]

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Récupération carte aléatoire via YGOPRODeck
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_random_card(card_type: str):
    url_type_map = {
        "monster": "Monster",
        "spell": "Spell%20Card",
        "trap": "Trap%20Card",
        "token": "Token"
    }
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?type={url_type_map[card_type]}&language=fr"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            cards = data.get("data", [])
            return random.choice(cards) if cards else None

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — View pour devinette
# ────────────────────────────────────────────────────────────────────────────────
class GuessView(discord.ui.View):
    def __init__(self, correct_card: dict, all_cards: list):
        super().__init__(timeout=30)
        self.correct_card = correct_card
        self.result_sent = False

        # Mélange des cartes pour boutons
        random.shuffle(all_cards)
        for card in all_cards:
            label = card.get("name", "Inconnu")
            self.add_item(GuessButton(label=label, card=card, parent=self))

class GuessButton(discord.ui.Button):
    def __init__(self, label, card, parent: GuessView):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.card = card
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction):
        if self.parent_view.result_sent:
            await interaction.response.send_message("⏳ Déjà répondu.", ephemeral=True)
            return

        self.parent_view.result_sent = True
        correct = self.card == self.parent_view.correct_card
        color = discord.Color.green() if correct else discord.Color.red()
        verdict = "✅ Bien joué ! Tu as deviné la bonne carte." if correct else f"❌ Mauvaise carte… C'était **{self.parent_view.correct_card.get('name')}**."

        embed = discord.Embed(
            title=f"{self.parent_view.correct_card.get('name')} ({self.parent_view.correct_card.get('type', '')})",
            description=self.parent_view.correct_card.get('desc', 'Pas de description.'),
            color=color
        )
        if "card_images" in self.parent_view.correct_card and self.parent_view.correct_card["card_images"]:
            embed.set_image(url=self.parent_view.correct_card["card_images"][0].get("image_url", ""))

        embed.set_footer(text=verdict)

        # Désactive tous les boutons
        for child in self.parent_view.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class DevineCarteButtons(commands.Cog):
    """
    Commande /devine_carte et !devine_carte — Devine la carte parmi 3-4 options
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_game(self, channel: discord.abc.Messageable, card_type: str):
        card_type = card_type.lower()
        if card_type not in CARD_TYPES:
            await safe_send(channel, f"❌ Type invalide. Choisis parmi : {', '.join(CARD_TYPES)}")
            return

        # Carte correcte
        correct_card = await fetch_random_card(card_type)
        if not correct_card:
            await safe_send(channel, "❌ Impossible de récupérer une carte. Réessaye plus tard.")
            return

        # Autres cartes pour les boutons (3-4 cartes total)
        options = [correct_card]
        while len(options) < 4:
            card = await fetch_random_card(card_type)
            if card and card not in options:
                options.append(card)

        embed = discord.Embed(
            title=f"🎰 Devine la carte ({card_type.capitalize()}) !",
            description="Clique sur le bouton correspondant à la bonne carte.",
            color=discord.Color.blurple()
        )
        await safe_send(channel, embed=embed, view=GuessView(correct_card, options))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="devine_carte",
        description="Devine la carte parmi 3-4 options (Monster/Spell/Trap/Token)."
    )
    @app_commands.describe(type="Type de carte à deviner")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_devine_carte(self, interaction: discord.Interaction, type: str):
        await interaction.response.defer()
        await self._run_game(interaction.channel, type)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="devine_carte")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_devine_carte(self, ctx: commands.Context, type: str):
        await self._run_game(ctx.channel, type)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = DevineCarteButtons(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
