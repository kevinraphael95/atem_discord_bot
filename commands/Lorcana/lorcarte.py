# ────────────────────────────────────────────────────────────────────────────────
# 📌 lorcarte.py — Commande /lorcarte et !lorcarte
# Objectif : Afficher une carte Disney Lorcana
# Catégorie : Lorcana
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import aiohttp
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Constantes API Lorcana
# ────────────────────────────────────────────────────────────────────────────────
LORCANA_API = "https://api.lorcana-api.com/cards"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class LorcanaCarte(commands.Cog):
    """Commande /lorcarte et !lorcarte — Affiche une carte Disney Lorcana"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Utilitaire API
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_card(self, name: str) -> dict | None:
        query = name.replace(" ", "_").lower()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{LORCANA_API}/{query}") as resp:
                if resp.status != 200:
                    return None
                return await resp.json()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Création de l'embed carte
    # ────────────────────────────────────────────────────────────────────────────
    def build_card_embed(self, card: dict) -> discord.Embed:
        name = card.get("name", "Carte inconnue")
        color = card.get("color", "?")
        cost = card.get("ink_cost", "?")
        types = ", ".join(card.get("types", []))
        strength = card.get("strength")
        willpower = card.get("willpower")
        lore = card.get("lore")
        text = card.get("rules_text", "")

        lines = [
            f"🎨 **Couleur** : {color}",
            f"💧 **Coût d'encre** : {cost}",
        ]

        if types:
            lines.append(f"🧩 **Types** : {types}")
        if strength is not None and willpower is not None:
            lines.append(f"⚔️ **Force / Volonté** : {strength} / {willpower}")
        if lore is not None:
            lines.append(f"✨ **Lore** : {lore}")
        if text:
            lines.append("\n📜 **Effet**")
            lines.append(text)

        embed = discord.Embed(
            title=name,
            description="\n".join(lines),
            color=discord.Color.purple()
        )

        images = card.get("image_uris", {})
        if "large" in images:
            embed.set_thumbnail(url=images["large"])

        embed.set_footer(text="Disney Lorcana • Source communautaire")
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="lorcarte", description="Affiche une carte Disney Lorcana")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_lorcarte(self, interaction: discord.Interaction, nom: str):
        await interaction.response.defer()

        data = await self.fetch_card(nom)
        if not data:
            await safe_respond(interaction, "❌ Carte introuvable.")
            return

        embed = self.build_card_embed(data)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="lorcarte")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_lorcarte(self, ctx: commands.Context, *, nom: str):
        data = await self.fetch_card(nom)
        if not data:
            await safe_send(ctx.channel, "❌ Carte introuvable.")
            return

        embed = self.build_card_embed(data)
        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = LorcanaCarte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "LorcanaTCG"
    await bot.add_cog(cog)
