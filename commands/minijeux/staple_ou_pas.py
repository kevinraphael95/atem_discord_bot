# ────────────────────────────────────────────────────────────────────────────────
# 📌 staple_ou_pas.py — Commande interactive /staple_ou_pas et !staple_ou_pas
# Objectif :
#   - Tire une carte aléatoire (50 % de chance d’être une staple)
#   - L’utilisateur doit deviner si c’est une staple ou non
#   - Le résultat s’affiche directement dans l’embed
# Catégorie : 🎮 Minijeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import random

from utils.discord_utils import safe_send, safe_respond
from utils.card_utils import fetch_random_card  # ✅ utilisation du module commun

# ────────────────────────────────────────────────────────────────────────────────
# 🔗 URLs API
# ────────────────────────────────────────────────────────────────────────────────
STAPLES_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes&language=fr"

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 View — Boutons de réponse
# ────────────────────────────────────────────────────────────────────────────────
class GuessView(discord.ui.View):
    def __init__(self, is_staple: bool, embed: discord.Embed, user: discord.User):
        super().__init__(timeout=15)
        self.is_staple = is_staple
        self.embed = embed
        self.user = user
        self.answered = False

    async def handle_guess(self, interaction: discord.Interaction, guess: bool):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Ce n’est pas ton tour !", ephemeral=True)
        if self.answered:
            return await interaction.response.send_message("⏳ Tu as déjà répondu.", ephemeral=True)

        self.answered = True
        correct = (guess == self.is_staple)

        if correct:
            result_text = "✅ **Bonne réponse !**"
            color = discord.Color.green()
        else:
            result_text = "❌ **Mauvaise réponse !**"
            color = discord.Color.red()

        true_text = "💎 Cette carte **est une Staple !**" if self.is_staple else "🪨 Cette carte **n’est pas une Staple.**"

        # Mise à jour de l’embed avec le résultat
        self.embed.color = color
        self.embed.add_field(name="Résultat", value=f"{result_text}\n{true_text}", inline=False)
        self.embed.set_footer(text="Fin de la manche")

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=self.embed, view=self)

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
    """
    Commande /staple_ou_pas et !staple_ou_pas — Devine si la carte est une staple ou pas
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_random_staple(self):
        """Récupère une carte staple aléatoire"""
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
        """Récupère une carte aléatoire (via utils/card_utils)"""
        card, lang = await fetch_random_card()
        return card

    async def play_round(self, interaction_or_ctx, is_slash: bool):
        """Logique commune entre slash et prefix"""
        await (safe_respond(interaction_or_ctx, "🔮 Tirage en cours...") if is_slash else safe_send(interaction_or_ctx, "🔮 Tirage en cours..."))

        # 50 % de chance d’être une staple
        is_staple = random.choice([True, False])
        card = await (self.get_random_staple() if is_staple else self.get_random_card())

        if not card:
            msg = "❌ Impossible de tirer une carte."
            return await (safe_respond(interaction_or_ctx, msg) if is_slash else safe_send(interaction_or_ctx, msg))

        name = card.get("name", "Carte inconnue")
        image_url = None
        if "card_images" in card and len(card["card_images"]) > 0:
            image_url = card["card_images"][0].get("image_url")

        embed = discord.Embed(
            title=f"🃏 {name}",
            description="💭 Devine si cette carte est une **Staple** ou non !",
            color=discord.Color.blurple()
        )
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text="Tu as 15 secondes pour répondre...")

        view = GuessView(is_staple, embed, interaction_or_ctx.user if is_slash else interaction_or_ctx.author)
        await (safe_respond(interaction_or_ctx, embed=embed, view=view) if is_slash else safe_send(interaction_or_ctx, embed=embed, view=view))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="staple_ou_pas",
        description="Devine si la carte tirée est une staple ou pas ! (50 % de chance)"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_staple_ou_pas(self, interaction: discord.Interaction):
        """Version slash de la commande"""
        await self.play_round(interaction, is_slash=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="staple_ou_pas", aliases=["sop"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_staple_ou_pas(self, ctx: commands.Context):
        """Version préfixe de la commande"""
        await self.play_round(ctx, is_slash=False)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = StapleOuPas(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
