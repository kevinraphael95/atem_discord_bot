# ────────────────────────────────────────────────────────────────────────────────
# 📌 topcarte.py
# Objectif : Mini-jeu — Classer 5 cartes Yu-Gi-Oh! dans un top 5 à l’aveugle
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes par utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import random

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue principale de classement
# ────────────────────────────────────────────────────────────────────────────────
class ClassementView(View):
    def __init__(self, bot, author, cartes):
        super().__init__(timeout=150)
        self.bot = bot
        self.author = author
        self.cartes = cartes
        self.index = 0
        self.classement = [None] * 5
        self.message = None
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        for i in range(5):
            if self.classement[i] is None:
                self.add_item(PositionButton(self, i))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

    async def update_message(self):
        carte = self.cartes[self.index]
        embed = discord.Embed(
            title=f"Carte {self.index + 1} / 5 : {carte['name']}",
            description=carte["desc"][:1000],
            color=discord.Color.gold()
        )
        if carte.get("image"):
            embed.set_image(url=carte["image"])
        embed.set_footer(text="Choisis sa position dans ton top 5")

        await safe_edit(self.message, embed=embed, view=self)

    async def assign_position(self, interaction, pos):
        if interaction.user != self.author:
            await interaction.response.send_message("⛔ Ce n'est pas à toi de jouer !", ephemeral=True)
            return

        if self.classement[pos] is not None:
            await interaction.response.send_message("❌ Position déjà prise.", ephemeral=True)
            return

        await interaction.response.defer()

        self.classement[pos] = self.cartes[self.index]
        self.index += 1

        if self.index >= len(self.cartes):
            await self.finish()
            self.stop()
        else:
            self._add_buttons()
            await self.update_message()

    async def finish(self):
        embed = discord.Embed(
            title="🏆 Ton Top 5 Final",
            color=discord.Color.green()
        )

        for i, carte in enumerate(self.classement):
            if carte:
                embed.add_field(
                    name=f"#{i+1} — {carte['name']}",
                    value=carte["desc"][:200] + "...",
                    inline=False
                )

        await safe_edit(
            self.message,
            content="Voici ton classement final :",
            embed=embed,
            view=ValidationView(self.author)
        )


# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Bouton de position
# ────────────────────────────────────────────────────────────────────────────────
class PositionButton(Button):
    def __init__(self, parent_view: ClassementView, position: int):
        super().__init__(label=f"#{position + 1}", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
        self.position = position

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.assign_position(interaction, self.position)


# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue de validation finale
# ────────────────────────────────────────────────────────────────────────────────
class ValidationView(View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="👍 Oui", style=discord.ButtonStyle.success)
    async def yes(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.author:
            await interaction.response.send_message("Ce n'est pas ton top !", ephemeral=True)
            return
        await interaction.response.edit_message(
            content="🟢 Parfait ! Content que ton top te plaise 😄",
            view=None
        )

    @discord.ui.button(label="👎 Non", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.author:
            await interaction.response.send_message("Ce n'est pas ton top !", ephemeral=True)
            return
        await interaction.response.edit_message(
            content="🔁 Peut-être plus de chance la prochaine fois 😈",
            view=None
        )


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec cooldown centralisé
# ────────────────────────────────────────────────────────────────────────────────
class TopCarte(commands.Cog):
    """
    Commande /topcarte et !topcarte — Mini-jeu Top 5 Yu-Gi-Oh!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Récupération des cartes aléatoires
    # ────────────────────────────────────────────────────────────────────────────
    async def _get_random_cards(self):
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                all_cards = data.get("data", [])
                sample = random.sample(all_cards, 5)

                return [
                    {
                        "name": c["name"],
                        "desc": c["desc"],
                        "image": c.get("card_images", [{}])[0].get("image_url")
                    }
                    for c in sample
                ]

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_game(self, channel, author):
        cartes = await self._get_random_cards()
        if not cartes:
            await safe_send(channel, "❌ Impossible de récupérer les cartes.")
            return

        view = ClassementView(self.bot, author, cartes)

        premiere = cartes[0]
        embed = discord.Embed(
            title=f"Carte 1 / 5 : {premiere['name']}",
            description=premiere['desc'][:1000],
            color=discord.Color.gold()
        )

        if premiere.get("image"):
            embed.set_image(url=premiere["image"])

        embed.set_footer(text="Classe cette carte dans ton top 5.")

        view.message = await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygotopcarte",
        description="Mini-jeu : Classe 5 cartes Yu-Gi-Oh! dans un top 5 à l’aveugle."
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_topcarte(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_game(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="ygotopcarte",
        aliases=["ygotopcarte", "ygotopcartes", "ytopc"],
        help="Mini-jeu : Classe 5 cartes Yu-Gi-Oh! dans un top 5 à l’aveugle."
    )
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_topcarte(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TopCarte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
