# ─────────────────────────────────────────────────────────────
# 📌 pcarte.py — Commande Pokémon TCG
# Objectif : Afficher une carte Pokémon TCG
# Catégorie : Pokémon TCG
# Accès : Public
# Cooldown : 3 sec / user
# ─────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from tcgdexsdk import TCGdex, Language
from tcgdexsdk.enums import Quality, Extension

from utils.discord_utils import safe_send

# ─────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ─────────────────────────────────────────────────────────────
class PokemonCarte(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tcgdex = TCGdex(Language.EN)  # Anglais par défaut, on peut changer en FR si voulu

    async def _show_card(self, channel: discord.abc.Messageable, query: str | None):
        card = None

        try:
            if not query or query.lower() == "random":
                # 🔀 Random : on récupère 1 carte aléatoire
                cards = await self.tcgdex.card.list()  # retourne toutes les cartes
                import random
                card = random.choice(cards)
                # Recharger la carte complète par son ID
                card = await self.tcgdex.card.get(card.id)

            elif "-" in query:
                # 🆔 ID direct
                card = await self.tcgdex.card.get(query)
            else:
                # 🔍 Recherche par nom (première correspondance)
                cards = await self.tcgdex.card.list(query=query)
                if cards:
                    card = await self.tcgdex.card.get(cards[0].id)

        except Exception as e:
            await safe_send(channel, f"❌ Une erreur est survenue : {e}")
            return

        if not card:
            await safe_send(channel, "❌ Carte introuvable.")
            return

        # ───────────────
        # 📊 Création embed
        # ───────────────
        embed = discord.Embed(
            title=f"{card.name} ({card.localId})",
            description=card.description or "Pas de description disponible",
            color=discord.Color.red()
        )

        if card.hp:
            embed.add_field(name="❤️ HP", value=str(card.hp), inline=True)

        if card.types:
            embed.add_field(name="🔮 Type(s)", value=", ".join(card.types), inline=True)

        embed.add_field(name="💎 Rareté", value=card.rarity or "Inconnue", inline=True)

        if card.set:
            embed.add_field(name="📦 Set", value=card.set.name, inline=True)

        # Variantes
        if card.variants:
            var_list = [k for k, v in card.variants.items() if v]
            if var_list:
                embed.add_field(name="🎭 Variantes", value=", ".join(var_list), inline=True)

        # Image
        image_url = card.get_image_url(Quality.HIGH, Extension.PNG)
        if image_url:
            embed.set_thumbnail(url=image_url)

        # Attaques
        if card.attacks:
            attacks_desc = ""
            for atk in card.attacks:
                cost = ", ".join(atk.cost) if atk.cost else "None"
                effect = atk.effect if atk.effect else ""
                dmg = atk.damage if atk.damage else ""
                attacks_desc += f"**{atk.name}** ({cost}) — {effect} {dmg}\n"
            embed.add_field(name="⚔️ Attaques", value=attacks_desc, inline=False)

        await safe_send(channel, embed=embed)

    # ─────────────────────────────────────────────────────────
    # 🔹 Slash command
    # ─────────────────────────────────────────────────────────
    @app_commands.command(
        name="pcarte",
        description="Afficher une carte Pokémon TCG (ou random)."
    )
    @app_commands.describe(query="Nom, ID (ex: swsh3-136) ou 'random'")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_pcarte(self, interaction: discord.Interaction, query: str = None):
        await interaction.response.defer()
        await self._show_card(interaction.channel, query)
        await interaction.delete_original_response()

    # ─────────────────────────────────────────────────────────
    # 🔹 Prefix command
    # ─────────────────────────────────────────────────────────
    @commands.command(name="pcarte", aliases=["pokemon"])
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_pcarte(self, ctx: commands.Context, *, query: str = None):
        await self._show_card(ctx.channel, query)

# ─────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ─────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PokemonCarte(bot)
    for cmd in cog.get_commands():
        cmd.category = "PokemonTCG"
    await bot.add_cog(cog)
