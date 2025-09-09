# ────────────────────────────────────────────────────────────────────────────────
# 📌 deck.py — Commande interactive /deck et !deck
# Objectif : Afficher un deck à partir d’un URL ydke:// ou d’un fichier .ydk
# Catégorie : Test
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from discord.abc import Messageable
from io import BytesIO
from datetime import datetime

from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.deck_utils import parse_url, parse_ydk_file, typed_deck_to_ydk, to_url, generate_deck_embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton pour YGOPRODECK
# ────────────────────────────────────────────────────────────────────────────────
class DeckButtonView(View):
    def __init__(self, out_url: str):
        super().__init__(timeout=120)
        self.add_item(Button(
            label="Upload to YGOPRODECK",
            style=discord.ButtonStyle.link,
            url=f"https://ygoprodeck.com/deckbuilder/?utm_source=bastion&y={out_url[7:]}"
        ))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class DeckCommand(commands.Cog):
    """
    Commande /deck et !deck — Affiche un deck à partir d’un URL ydke:// ou d’un fichier .ydk
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _process_deck(
        self,
        interaction_or_ctx,
        url: str = None,
        file: discord.Attachment = None,
        stacked: bool = False
    ):
        start_time = datetime.utcnow()
        try:
            if url:
                deck = parse_url(url)
            elif file:
                if not file.filename.endswith(".ydk"):
                    await safe_edit(interaction_or_ctx, "❌ Le fichier doit avoir l’extension .ydk !")
                    return
                content = await file.read()
                deck = parse_ydk_file(BytesIO(content))
            else:
                await safe_edit(interaction_or_ctx, "❌ Vous devez fournir un URL ou un fichier .ydk.")
                return

            if not (deck.main or deck.extra or deck.side):
                await safe_edit(interaction_or_ctx, "❌ Votre deck est vide.")
                return

            out_url = to_url(deck)
            out_file = typed_deck_to_ydk(deck)
            embed = generate_deck_embed(deck, stacked, out_url)
            attachment = discord.File(BytesIO(out_file.encode("utf-8")), filename="deck.ydk")
            view = DeckButtonView(out_url)

            await safe_edit(interaction_or_ctx, embed=embed, files=[attachment], view=view)
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            return latency

        except Exception as e:
            await safe_edit(interaction_or_ctx, f"❌ Une erreur est survenue : {e}")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="deckk",
        description="Affiche un deck à partir d’un URL ydke:// ou d’un fichier .ydk"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_deck(
        self,
        interaction: discord.Interaction,
        url: str = None,
        file: discord.Attachment = None,
        stacked: bool = False
    ):
        """Commande slash principale."""
        await interaction.response.defer()
        await self._process_deck(interaction, url=url, file=file, stacked=stacked)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="deckk")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_deck(
        self,
        ctx: commands.Context,
        url: str = None,
        file: discord.Attachment = None,
        stacked: bool = False
    ):
        """Commande préfixe principale."""
        await self._process_deck(ctx, url=url, file=file, stacked=stacked)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = DeckCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
