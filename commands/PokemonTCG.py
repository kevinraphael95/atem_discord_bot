# ─────────────────────────────────────────────────────────────
# 📌 pcarte.py — Commande Pokémon TCG
# Objectif : Afficher une carte Pokémon (ou random)
# Catégorie : 🃏 Pokémon TCG
# Accès : Public
# Cooldown : 1 / 3 sec
# ─────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send
from utils.pokemon_utils import (
    fetch_card_by_name,
    fetch_card_by_id,
    fetch_random_card
)

# ─────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ─────────────────────────────────────────────────────────────
class PokemonCarte(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _show_card(self, channel, query: str | None):
        session = self.bot.aiohttp_session

        # 🔀 Random
        if not query or query.lower() == "random":
            card = await fetch_random_card(session)
        # 🆔 ID direct
        elif "-" in query:
            card = await fetch_card_by_id(query, session)
        # 🔍 Recherche par nom
        else:
            card = await fetch_card_by_name(query, session)

        if not card:
            await safe_send(channel, "❌ Carte introuvable.")
            return

        # ───────────────
        # 📊 Infos carte
        # ───────────────
        name = card.get("name", "Carte inconnue")
        hp = card.get("hp")
        types = card.get("types", [])
        rarity = card.get("rarity", "Inconnue")
        image = card.get("image")
        set_data = card.get("set", {})
        variants = card.get("variants", {})
        pricing = card.get("pricing", {})

        desc_lines = []

        if hp:
            desc_lines.append(f"❤️ **HP** : {hp}")

        if types:
            desc_lines.append(f"🔮 **Type(s)** : {', '.join(types)}")

        desc_lines.append(f"💎 **Rareté** : {rarity}")

        if set_data:
            desc_lines.append(f"📦 **Set** : {set_data.get('name')}")

        # 🎭 Variantes
        if variants:
            v = [k for k, v in variants.items() if v]
            if v:
                desc_lines.append(f"🎭 **Variantes** : {', '.join(v)}")

        # 💰 Prix
        if pricing.get("cardmarket"):
            cm = pricing["cardmarket"]
            desc_lines.append(
                f"💰 **Prix (Cardmarket)** : {cm.get('avg', '?')} €"
            )

        embed = discord.Embed(
            title=name,
            description="\n".join(desc_lines),
            color=discord.Color.red()
        )

        if image:
            embed.set_thumbnail(url=image)

        await safe_send(channel, embed=embed)

    # ─────────────────────────────────────────────────────────
    # 🔹 Slash command
    # ─────────────────────────────────────────────────────────
    @app_commands.command(
        name="pcarte",
        description="Afficher une carte Pokémon TCG (ou random)."
    )
    @app_commands.describe(nom="Nom, ID (ex: swsh3-136) ou 'random'")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_pcarte(self, interaction: discord.Interaction, nom: str = None):
        await interaction.response.defer()
        await self._show_card(interaction.channel, nom)
        await interaction.delete_original_response()

    # ─────────────────────────────────────────────────────────
    # 🔹 Prefix command
    # ─────────────────────────────────────────────────────────
    @commands.command(name="pcarte", aliases=["pokemon"])
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_pcarte(self, ctx: commands.Context, *, nom: str = None):
        await self._show_card(ctx.channel, nom)

# ─────────────────────────────────────────────────────────────
# 🔌 Setup
# ─────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PokemonCarte(bot)
    for cmd in cog.get_commands():
        cmd.category = "PokemonTCG"
    await bot.add_cog(cog)
