# ────────────────────────────────────────────────────────────────────────────────
# 📌 art.py — Commande interactive !art
# Objectif :
#   - Afficher les illustrations d’une carte Yu-Gi-Oh!
#   - Permettre de naviguer entre plusieurs illustrations si disponibles
#   - Utilise utils/card_utils pour la recherche
# Catégorie :
#   - 
# Accès :
#   - Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send
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
    """Commande !art — Affiche les illustrations d’une carte Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="art",
        help="🎨 Affiche les illustrations d’une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT).",
        description="Permet de naviguer entre plusieurs illustrations si disponibles."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def art(self, ctx: commands.Context, *, nom: str):
        carte, langue, message = await search_card(nom)

        if message:  # Message d’erreur ou d’avertissement
            await safe_send(ctx, message)
            return

        if not carte:
            await safe_send(ctx, f"❌ Impossible de trouver la carte `{nom}`.")
            return

        # Récupération des illustrations
        images = [img.get("image_url") for img in carte.get("card_images", []) if img.get("image_url")]
        if not images:
            await safe_send(ctx, "❌ Aucune illustration disponible pour cette carte.")
            return

        titre = f"{carte.get('name', 'Carte inconnue')} ({langue.upper()})"
        embed = discord.Embed(
            title=f"{titre} — Illustration 1/{len(images)}",
            color=discord.Color.purple()
        )
        embed.set_image(url=images[0])

        await safe_send(ctx, embed=embed, view=ArtPagination(images, titre))


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Art(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
