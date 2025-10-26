# ────────────────────────────────────────────────────────────────────────────────
# 📌 art.py — Commande interactive !art
# Objectif :
#   - Afficher les illustrations d’une carte Yu-Gi-Oh!
#   - Utiliser la recherche centralisée dans utils/card_utils.py
#   - Pagination entre les différentes illustrations
# Catégorie : 🎨 Illustrations
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.discord_utils import safe_send
from utils.card_utils import search_card  # ✅ Utilisation du module centralisé

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination des illustrations
# ────────────────────────────────────────────────────────────────────────────────
class ArtPagination(View):
    def __init__(self, images: list[str], card_name: str):
        super().__init__(timeout=120)
        self.images = images
        self.index = 0
        self.card_name = card_name

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{self.card_name} — Illustration {self.index+1}/{len(self.images)}",
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
        # ── Recherche centralisée via card_utils ────────────────────────────────
        carte, langue, msg = await search_card(nom)
        if not carte:
            await safe_send(ctx.channel, msg or f"❌ Carte introuvable pour `{nom}`.")
            return

        # ── Récupération des images ─────────────────────────────────────────────
        images = [img.get("image_url") for img in carte.get("card_images", []) if img.get("image_url")]
        if not images:
            await safe_send(ctx.channel, "❌ Aucune illustration disponible pour cette carte.")
            return

        # ── Embed initial ───────────────────────────────────────────────────────
        card_name = carte.get("name", "Carte inconnue")
        embed = discord.Embed(
            title=f"{card_name} — Illustration 1/{len(images)}",
            color=discord.Color.purple()
        )
        embed.set_image(url=images[0])
        embed.set_footer(text=f"Langue : {langue.upper()}")

        await safe_send(ctx.channel, embed=embed, view=ArtPagination(images, card_name))

    def cog_load(self):
        self.art.category = "🎨 Illustrations"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Art(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
