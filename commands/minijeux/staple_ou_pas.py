# ────────────────────────────────────────────────────────────────────────────────
# 📌 staple_ou_pas.py — Minijeu interactif !staple_ou_pas
# Objectif :
#   - Tire une carte aléatoire (staple ou non)
#   - L’utilisateur doit deviner si elle est une staple
#   - 50% de chances qu’elle le soit réellement
# Catégorie : 🎮 Minijeux
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands
import aiohttp
import random
from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 URLs API
# ────────────────────────────────────────────────────────────────────────────────
ALL_CARDS_API = "https://db.ygoprodeck.com/api/v7/randomcard.php"
STAPLES_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes&language=fr"

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 View — boutons de réponse
# ────────────────────────────────────────────────────────────────────────────────
class GuessView(discord.ui.View):
    def __init__(self, is_staple: bool, user: discord.User):
        super().__init__(timeout=15)
        self.is_staple = is_staple
        self.user = user
        self.answered = False

    async def handle_guess(self, interaction: discord.Interaction, guess: bool):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Ce n’est pas ton tour !", ephemeral=True)
        if self.answered:
            return await interaction.response.send_message("⏳ Tu as déjà répondu.", ephemeral=True)

        self.answered = True
        result = (guess == self.is_staple)
        msg = "✅ Bonne réponse ! C’était bien une **Staple** !" if result and self.is_staple else \
              "✅ Bonne réponse ! Ce n’était **pas** une staple !" if result else \
              "❌ Mauvaise réponse !"

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(label="Staple", style=discord.ButtonStyle.success, emoji="💎")
    async def guess_staple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_guess(interaction, True)

    @discord.ui.button(label="Pas Staple", style=discord.ButtonStyle.danger, emoji="🪨")
    async def guess_not_staple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_guess(interaction, False)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class StapleOuPas(commands.Cog):
    """Commande !staple_ou_pas — Devine si la carte est une staple ou pas"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_random_staple(self):
        """Tire une carte aléatoire parmi les staples"""
        async with aiohttp.ClientSession() as session:
            async with session.get(STAPLES_API) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                cards = data.get("data", [])
                if not cards:
                    return None
                return random.choice(cards)

    async def get_random_card(self):
        """Tire une carte aléatoire quelconque"""
        async with aiohttp.ClientSession() as session:
            async with session.get(ALL_CARDS_API) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()

    @commands.command(
        name="staple_ou_pas", aliases=["sop"],
        help="🎮 Devine si la carte tirée est une staple ou pas (50 % de chance !)"
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def staple_ou_pas(self, ctx: commands.Context):
        await safe_send(ctx, "🔮 Tirage en cours...")

        # 50% de chances de tirer une staple
        is_staple = random.choice([True, False])
        card = await (self.get_random_staple() if is_staple else self.get_random_card())

        if not card:
            return await safe_send(ctx, "❌ Impossible de tirer une carte.")

        name = card.get("name", "Carte inconnue")
        desc = card.get("desc", "Pas de description disponible.")
        image_url = None

        if "card_images" in card and card["card_images"]:
            image_url = card["card_images"][0].get("image_url")

        embed = discord.Embed(
            title=f"🃏 {name}",
            description=f"Devine si cette carte est une **Staple** ou non !",
            color=discord.Color.random()
        )
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text="Tu as 15 secondes pour répondre...")

        view = GuessView(is_staple, ctx.author)
        await safe_send(ctx, embed=embed, view=view)

    def cog_load(self):
        self.staple_ou_pas.category = "🎮 Minijeux"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = StapleOuPas(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
