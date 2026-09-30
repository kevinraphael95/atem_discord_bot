# ================================================================================
# 📌 roulette_devine.py
# Objectif : Tire une carte aléatoire via roulette YGO et devine le type
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 5 secondes
# Version optimisée : safe_defer + 1 appel API
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import random

from utils.discord_utils import safe_send, safe_edit, safe_defer
from utils.card_utils import fetch_cards_by_type

# ================================================================================
# 🎰 Roulette : types + poids
# ================================================================================
ROULETTE = [
    ("monster", 33),
    ("spell", 33),
    ("trap", 33),
    ("token", 1),
]

def spin_roulette():
    types, weights = zip(*ROULETTE)
    return random.choices(types, weights=weights, k=1)[0]

# ================================================================================
# 🎛️ UI — Deviner le type de carte
# ================================================================================
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
        verdict = (
            "✅ Bien joué ! Tu as deviné le type."
            if correct
            else f"❌ Mauvaise devinette… C'était **{self.parent_view.correct_type.capitalize()}**."
        )

        embed = discord.Embed(
            title=f"{self.parent_view.card.get('name', 'Carte inconnue')} ({self.parent_view.correct_type.capitalize()})",
            description=self.parent_view.card.get("desc", "Pas de description."),
            color=color
        )
        if "card_images" in self.parent_view.card and self.parent_view.card["card_images"]:
            embed.set_image(url=self.parent_view.card["card_images"][0].get("image_url", ""))

        embed.set_footer(text=verdict)

        for child in self.parent_view.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class RouletteDevine(commands.Cog):
    """Commande /ygoroulette et !ygoroulette — Tire une carte et devine le type"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction commune
    # ============================================================================
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

        # ✅ Utilise card_utils (session partagée, 1 appel API)
        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return await safe_send(channel, "❌ Session HTTP non disponible.")

        type_map = {
            "monster": "Monster",
            "spell": "Spell Card",
            "trap": "Trap Card",
            "token": "Token"
        }
        cards = await fetch_cards_by_type(session, type_map[card_type], n=1)
        if not cards:
            return await safe_send(channel, "❌ Impossible de récupérer une carte. Réessaye plus tard.")

        card = cards[0]
        await safe_send(channel, embed=embed, view=GuessTypeView(card_type, card))

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ygoroulette",
        description="Tire une carte YGO et devine son type !"
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_roulette_devine(self, interaction: discord.Interaction):
        # ✅ Defer sécurisé
        if not await safe_defer(interaction):
            return
        await self._run_roulette(interaction.channel)
        # Pas de delete, defer = invisible

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="ygoroulette", help="Tire une carte YGO et devine son type !")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_roulette_devine(self, ctx: commands.Context):
        await self._run_roulette(ctx.channel)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = RouletteDevine(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
