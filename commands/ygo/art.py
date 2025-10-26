# ────────────────────────────────────────────────────────────────────────────────
# 📌 art.py — Commande interactive !art
# Objectif :
#   - Afficher les illustrations d’une carte Yu-Gi-Oh!
#   - Permettre de naviguer entre plusieurs illustrations si disponibles
# - Thumbnail ou image principale
# - Pagination pour artworks alternatifs
# Catégorie : 
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import urllib.parse
import json
from pathlib import Path
from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Helpers
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_card_multilang(nom: str) -> dict:
    nom_encode = urllib.parse.quote(nom)
    languages = ["fr", "de", "it", "pt", ""]
    async with aiohttp.ClientSession() as session:
        for lang in languages:
            url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
            if lang:
                url += f"&language={lang}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        return data["data"][0]
    return None

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination des illustrations
# ────────────────────────────────────────────────────────────────────────────────
class ArtPagination(View):
    def __init__(self, images: list[str]):
        super().__init__(timeout=120)
        self.images = images
        self.index = 0

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"Illustration {self.index+1}/{len(self.images)}",
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
        carte = await fetch_card_multilang(nom)
        if not carte:
            await safe_send(ctx.channel, f"❌ Carte introuvable pour `{nom}`.")
            return

        # Récupération des images
        images = [img.get("image_url") for img in carte.get("card_images", []) if img.get("image_url")]
        if not images:
            await safe_send(ctx.channel, "❌ Aucune illustration disponible pour cette carte.")
            return

        # Embed initial
        embed = discord.Embed(
            title=f"{carte.get('name', 'Carte inconnue')} — Illustration 1/{len(images)}",
            color=discord.Color.purple()
        )
        embed.set_image(url=images[0])
        await safe_send(ctx.channel, embed=embed, view=ArtPagination(images))

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
