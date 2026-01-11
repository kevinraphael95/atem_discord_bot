# ────────────────────────────────────────────────────────────────────────────────
# 📌 topcarte.py — Commande interactive !topcarte
# Objectif : Classe 5 cartes Yu-Gi-Oh! dans un top 5, une à une, sans connaître les prochaines.
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import random
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue principale de classement
# ────────────────────────────────────────────────────────────────────────────────
class ClassementView(View):
    def __init__(self, bot, ctx, cartes, index=0, classement=None):
        super().__init__(timeout=150)
        self.bot = bot
        self.ctx = ctx
        self.cartes = cartes
        self.index = index
        self.classement = classement or [None] * 5  # Top 5 vide

        for i in range(5):
            if self.classement[i] is None:
                self.add_item(PositionButton(self, i))

    async def update_message(self, interaction):
        carte = self.cartes[self.index]
        embed = discord.Embed(
            title=f"Carte {self.index + 1} / 5 : {carte['name']}",
            description=carte["desc"][:1000],
            color=discord.Color.gold()
        )
        if carte.get("image"):
            embed.set_image(url=carte["image"])
        embed.set_footer(text="Choisis sa position dans ton top 5")
        await safe_edit(interaction.message, embed=embed, view=self)

    async def assign_position(self, interaction, pos):
        if self.classement[pos] is not None:
            await interaction.response.send_message("❌ Cette position est déjà prise.", ephemeral=True)
            return

        self.classement[pos] = self.cartes[self.index]
        self.index += 1

        if self.index == len(self.cartes):
            await self.fin(interaction)
            self.stop()
        else:
            self.clear_items()
            for i in range(5):
                if self.classement[i] is None:
                    self.add_item(PositionButton(self, i))
            await self.update_message(interaction)

    async def fin(self, interaction):
        embed = discord.Embed(
            title="🟢 Ton Top 5 Final",
            color=discord.Color.green()
        )
        for i, carte in enumerate(self.classement):
            if carte:
                embed.add_field(
                    name=f"#{i+1} - {carte['name']}",
                    value=carte["desc"][:200] + "...",
                    inline=False
                )
        await safe_edit(interaction.message, content="Voici ton classement final :", embed=embed, view=None)
        await safe_send(self.ctx.channel, "🔍 Es-tu satisfait de ton top 5 ?", view=ValidationView(self.ctx.author))

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton de classement
# ────────────────────────────────────────────────────────────────────────────────
class PositionButton(Button):
    def __init__(self, parent_view: ClassementView, position: int):
        super().__init__(label=f"#{position + 1}", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
        self.position = position

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.ctx.author:
            await interaction.response.send_message("⛔ Ce n'est pas à toi de jouer !", ephemeral=True)
            return
        await interaction.response.defer()
        await self.parent_view.assign_position(interaction, self.position)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue de validation finale (satisfait ou non ?)
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
        await interaction.response.edit_message(content="🟩 Parfait, content que ça te plaise !", view=None)

    @discord.ui.button(label="👎 Non", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.author:
            await interaction.response.send_message("Ce n'est pas ton top !", ephemeral=True)
            return
        await interaction.response.edit_message(content="🔁 Peut-être que tu auras plus de chance la prochaine fois !", view=None)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TopCarte(commands.Cog):
    """
    Commande !topcarte — Classe 5 cartes dans un top 5, une à une.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_random_cards(self):
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

    @commands.command(
        name="topcarte", aliases = ["topcartes", "topc"], 
        help="Mini-jeu : Classe 5 cartes Yu-Gi-Oh! dans un top 5 à l’aveugle.",
        description="Le bot te montre 5 cartes une à une, tu les places dans ton top."
    )
    async def topcarte(self, ctx: commands.Context):
        """Commande principale du mini-jeu."""
        try:
            cartes = await self.get_random_cards()
            if not cartes:
                await safe_send(ctx.channel, "❌ Impossible de récupérer les cartes.")
                return

            view = ClassementView(self.bot, ctx, cartes)
            premiere = cartes[0]
            embed = discord.Embed(
                title=f"Carte 1 / 5 : {premiere['name']}",
                description=premiere['desc'][:1000],
                color=discord.Color.gold()
            )
            if premiere.get("image"):
                embed.set_image(url=premiere["image"])
            embed.set_footer(text="Classe cette carte dans ton top 5.")

            await safe_send(ctx.channel, embed=embed, view=view)

        except Exception as e:
            print(f"[ERREUR topcarte] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue pendant le mini-jeu.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TopCarte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
