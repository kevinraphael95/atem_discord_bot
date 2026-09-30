# ================================================================================
# 📌 art.py
# Objectif :
#   - Afficher les illustrations d'une carte Yu-Gi-Oh!
#   - Naviguer entre plusieurs illustrations si disponibles
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 3 sec / utilisateur
# Version optimisée : safe_defer + fetch_card_full (1 appel API)
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_defer
from utils.card_utils import fetch_card_full

# ================================================================================
# 🎛️ View — Pagination des illustrations
# ================================================================================
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

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Art(commands.Cog):
    """Commande /ygoart et !ygoart — Affiche les illustrations d'une carte Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _show_art(self, channel: discord.abc.Messageable, nom: str):
        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return await safe_send(channel, "❌ Session HTTP non disponible.")

        # ✅ 1 seul appel API
        carte = await fetch_card_full(nom, session)
        if not carte:
            return await safe_send(channel, f"❌ Impossible de trouver la carte `{nom}`.")

        images = []
        for img in carte.get("card_images", []):
            cropped = img.get("image_url_cropped")
            full = img.get("image_url")
            if cropped:
                images.append(cropped)
            elif full:
                images.append(full)

        if not images:
            return await safe_send(channel, "❌ Aucune illustration disponible pour cette carte.")

        card_name = carte.get("name_fr") or carte.get("name", "Carte inconnue")

        embed = discord.Embed(
            title=f"{card_name} — Illustration 1/{len(images)}",
            color=discord.Color.purple()
        )
        embed.set_image(url=images[0])

        if len(images) > 1:
            await safe_send(channel, embed=embed, view=ArtPagination(images, card_name))
        else:
            await safe_send(channel, embed=embed)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ygoart",
        description="Affiche les illustrations d'une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT)."
    )
    @app_commands.describe(nom="Nom de la carte")
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_art(self, interaction: discord.Interaction, nom: str):
        # ✅ Defer sécurisé
        if not await safe_defer(interaction):
            return
        await self._show_art(interaction.channel, nom)
        # Pas besoin de delete, le defer est invisible

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="ygoart",
        aliases=["yart"],
        help="🎨 Affiche les illustrations d'une carte Yu-Gi-Oh! (FR/EN/DE/PT/IT)."
    )
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_art(self, ctx: commands.Context, *, nom: str):
        await self._show_art(ctx.channel, nom)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Art(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
