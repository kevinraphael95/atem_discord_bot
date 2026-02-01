# ────────────────────────────────────────────────────────────────────────────────
# 📌 roulette_devine.py
# Objectif : Tire une carte aléatoire via roulette YGO (Monster/Spell/Trap/Token) et devine le type
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 5 secondes
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import random

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎰 Roulette : types + poids
# ────────────────────────────────────────────────────────────────────────────────
ROULETTE = [
    ("monster", 33),
    ("spell", 33),
    ("trap", 33),
    ("token", 1),
]

def spin_roulette():
    types, weights = zip(*ROULETTE)
    return random.choices(types, weights=weights, k=1)[0]

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
# 🎛️ UI — Deviner le type de carte
# ────────────────────────────────────────────────────────────────────────────────
class GuessTypeView(discord.ui.View):
    def __init__(self, correct_type: str, card: dict):
        super().__init__(timeout=30)
        self.correct_type = correct_type
        self.card = card
        self.guessed = False

        for t in ["monster", "spell", "trap", "token"]:
            self.add_item(GuessButton(label=t.capitalize(), guess_type=t, parent=self))

class GuessButton(discord.ui.Button):
    def __init__(self, label: str, guess_type: str, parent: GuessTypeView):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.guess_type = guess_type
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction):
        if self.parent_view.guessed:
            await interaction.response.send_message("⏳ Déjà deviné !", ephemeral=True)
            return
        self.parent_view.guessed = True

        correct = self.guess_type == self.parent_view.correct_type
        color = discord.Color.green() if correct else discord.Color.red()
        verdict = "✅ Bien joué ! Tu as deviné le type." if correct else f"❌ Mauvaise devinette… C'était **{self.parent_view.correct_type.capitalize()}**."

        embed = discord.Embed(
            title=f"{self.parent_view.card.get('name', 'Carte inconnue')} ({self.parent_view.correct_type.capitalize()})",
            description=self.parent_view.card.get("desc", "Pas de description."),
            color=color
        )
        if "card_images" in self.parent_view.card and self.parent_view.card["card_images"]:
            embed.set_image(url=self.parent_view.card["card_images"][0].get("image_url", ""))

        embed.set_footer(text=verdict)

        # Désactive les boutons
        for child in self.parent_view.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class RouletteDevine(commands.Cog):
    """
    Commande /roulette_devine et !roulette_devine — Tire une carte aléatoire via roulette pondérée et devine le type
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_roulette(self, channel: discord.abc.Messageable):
        embed = discord.Embed(
            title="🎰 Roulette YGO",
            description=(
                "Clique sur le bouton correspondant au **type de carte** que tu penses être tiré !\n\n"
                "• 33% Monstre\n"
                "• 33% Magie\n"
                "• 33% Piège\n"
                "• 1% Jeton"
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Tu as 30 secondes pour deviner… Ding ding ding !")

        # Tirage réel de la roulette
        card_type = spin_roulette()
        card = await fetch_random_card(card_type)
        if not card:
            await safe_send(channel, "❌ Impossible de récupérer une carte. Réessaye plus tard.")
            return

        await safe_send(channel, embed=embed, view=GuessTypeView(card_type, card))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="roulette",
        description="Tire une carte aléatoire et devine son type (Monstre/Magie/Piège/Jeton)."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_roulette_devine(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._run_roulette(interaction.channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="roulette")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_roulette_devine(self, ctx: commands.Context):
        await self._run_roulette(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RouletteDevine(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
