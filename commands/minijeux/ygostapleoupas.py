# ────────────────────────────────────────────────────────────────────────────────
# 📌 staple_ou_pas.py
# Objectif : Tire une carte aléatoire et l'utilisateur doit deviner si c'est une staple
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View
import random

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_followup

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Boutons de réponse
# ────────────────────────────────────────────────────────────────────────────────
class GuessView(View):
    def __init__(self, is_staple: bool, embed: discord.Embed, user: discord.User):
        super().__init__(timeout=15)
        self.is_staple = is_staple
        self.embed = embed
        self.user = user
        self.answered = False
        self.message = None

    async def on_timeout(self):
        if self.answered:
            return
        self.answered = True
        true_text = "💎 Cette carte **est une Staple !**" if self.is_staple else "🪨 Cette carte **n'est pas une Staple.**"
        self.embed.color = discord.Color.greyple()
        self.embed.add_field(name="Résultat", value=f"⏳ **Temps écoulé !**\n{true_text}", inline=False)
        self.embed.set_footer(text="Fin de la manche")
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, embed=self.embed, view=self)

    async def handle_guess(self, interaction: discord.Interaction, guess: bool):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Ce n'est pas ton tour !", ephemeral=True)
        if self.answered:
            return await interaction.response.send_message("⏳ Tu as déjà répondu.", ephemeral=True)
        self.answered = True

        correct = (guess == self.is_staple)
        color = discord.Color.green() if correct else discord.Color.red()
        result_text = "✅ **Bonne réponse !**" if correct else "❌ **Mauvaise réponse !**"
        true_text = "💎 Cette carte **est une Staple !**" if self.is_staple else "🪨 Cette carte **n'est pas une Staple.**"

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
    """Commande /staple_ou_pas et !staple_ou_pas — Devine si la carte est une staple ou pas"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────
    # 🔹 Helpers pour récupérer les cartes
    # ────────────────────────────────────────────────────────────
    async def get_random_staple(self):
        """Tire une carte parmi les vraies staples."""
        async with self.bot.aiohttp_session.get(
            "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes&language=fr"
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            cards = data.get("data", [])
            return random.choice(cards) if cards else None

    async def get_random_non_staple(self):
        """
        Tire une carte aléatoire qui N'EST PAS une staple.
        On retire les staples du pool AVANT de tirer, pour éviter
        de tomber par hasard sur une staple quand is_staple=False.
        """
        async with self.bot.aiohttp_session.get(
            "https://db.ygoprodeck.com/api/v7/cardinfo.php?random=yes&language=fr"
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            cards = data.get("data", [])

        # Retire les cartes marquées staple pour garantir la cohérence du jeu
        non_staples = [c for c in cards if not c.get("staple")]
        if non_staples:
            return random.choice(non_staples)
        return random.choice(cards) if cards else None

    async def build_embed(self, card: dict) -> discord.Embed:
        name = card.get("name", "Carte inconnue")
        color = discord.Color.blue()
        desc = card.get("desc", "Pas de description disponible.")
        embed = discord.Embed(title=f"**{name}**", description=desc, color=color)
        if "card_images" in card and card["card_images"]:
            embed.set_thumbnail(
                url=card["card_images"][0].get("image_url_cropped")
                    or card["card_images"][0].get("image_url")
            )
        embed.set_footer(text="💭 Devine si cette carte est une Staple ou non !")
        return embed

    # ────────────────────────────────────────────────────────────
    # 🔹 Partie commune slash / prefix
    # ────────────────────────────────────────────────────────────
    async def play_round(self, ctx_or_inter, is_slash: bool):
        is_staple = random.choice([True, False])
        card = await (self.get_random_staple() if is_staple else self.get_random_non_staple())
        if not card:
            msg = "❌ Impossible de tirer une carte."
            return await (safe_followup(ctx_or_inter, msg) if is_slash else safe_send(ctx_or_inter, msg))

        embed = await self.build_embed(card)
        view = GuessView(is_staple, embed, ctx_or_inter.user if is_slash else ctx_or_inter.author)

        if is_slash:
            sent = await safe_followup(ctx_or_inter, embed=embed, view=view)
        else:
            sent = await safe_send(ctx_or_inter, embed=embed, view=view)
        view.message = sent

    # ────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygosop",
        description="Devine si la carte tirée est une staple ou pas !"
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_staple_ou_pas(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.play_round(interaction, True)

    # ────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────
    @commands.command(
        name="ygosop",
        aliases=["ysop", "ygo_sop", "ygo_staple_ou_pas"],
        help="Devine si la carte tirée est une staple ou pas !"
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_staple_ou_pas(self, ctx: commands.Context):
        await self.play_round(ctx, False)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = StapleOuPas(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
