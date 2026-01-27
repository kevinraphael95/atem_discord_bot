# ────────────────────────────────────────────────────────────────────────────────
# 📌 art.py
# Objectif :
#   - Afficher les illustrations d’une carte Yu-Gi-Oh!
#   - Permettre de naviguer entre plusieurs illustrations si disponibles
#   - Utilise utils/card_utils pour la recherche
# Catégorie :
#   - 🃏 Yu-Gi-Oh!
# Accès :
#   - Public
# Cooldown :
#   - 1 utilisation / 3 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_respond
from utils.card_utils import search_card

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination des illustrations
# ────────────────────────────────────────────────────────────────────────────────
class ArtPagination(View):
    """Interface de navigation entre plusieurs illustrations."""
    def __init__(self, images: list[str], titre: str):
        super().__init__(timeout=120)
        self.images = images
        self.index = 0
        self.titre = titre

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{self.titre} — Illustration {self.index + 1}/{len(self.images)}",
            color=discord.Color.purple()
        )
        embed.set_image(url=self.images[self.index])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.images)
        await self.update_embed(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(self.images)
        await self.update_embed(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Art(commands.Cog):
    """Commande /art et !art — Affiche les illustrations d’une carte Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _show_art(self, channel: discord.abc.Messageable, nom: str):
        carte, langue, message = await search_card(nom, self.bot.aiohttp_session)
        if message:
            await safe_send(channel, message)
            return
        if not carte:
            await safe_send(channel, f"❌ Impossible de trouver la carte `{nom}`.")
            return

        images = []
        for img in carte.get("card_images", []):
            cropped = img.get("image_url_cropped")
            full = img.get("image_url")
            if cropped:
                images.append(cropped)
            elif full:
                images.append(full)

        if not images:
            await safe_send(channel, "❌ Aucune illustration disponible pour cette carte.")
            return

        titre = f"{carte.get('name', 'Carte inconnue')} ({langue.upper()})"
        embed = discord.Embed(
            title=f"{titre} — Illustration 1/{len(images)}",
            color=discord.Color.purple()
        )
        embed.set_image(url=images[0])
        await safe_send(channel, embed=embed, view=ArtPagination(images, titre))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="art",
        description="Affiche les illustrations d’une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT)."
    )
    @app_commands.describe(nom="Nom de la carte")
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_art(self, interaction: discord.Interaction, nom: str):
        await interaction.response.defer()
        await self._show_art(interaction.channel, nom)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="art",
        help="🎨 Affiche les illustrations d’une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT).",
        description="Permet de naviguer entre plusieurs illustrations si disponibles."
    )
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_art(self, ctx: commands.Context, *, nom: str):
        await self._show_art(ctx.channel, nom)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Art(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
