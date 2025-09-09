# ────────────────────────────────────────────────────────────────────────────────
# 📌 search.py — Commande interactive /search et !search
# Objectif : Trouver toutes les informations d'une carte
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
from utils.discord_utils import safe_send, safe_respond
from utils.card_utils import get_card, create_card_embed, get_card_search_options, should_exclude_icons
from utils.metrics_utils import reply_latency
from utils.locale_utils import use_locale
from utils.limit_regulation import master_duel_limit_regulation

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class SearchCommand(commands.Cog):
    """
    Commande /search et !search — Trouver toutes les informations d'une carte
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="search",
        description="Find all information on a card!"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_search(self, interaction: discord.Interaction, term: str):
        """Commande slash principale pour rechercher une carte."""
        try:
            await interaction.response.defer()
            search_options = await get_card_search_options(interaction)
            type_, input_, result_language, input_language = (
                search_options['type'],
                search_options['input'],
                search_options['result_language'],
                search_options['input_language']
            )

            card = await get_card(type_, input_, input_language)
            if not card:
                use_locale(result_language)
                reply_content = f"❌ Could not find a card matching `{input_}`!"
                await safe_respond(interaction, reply_content)
            else:
                embeds = create_card_embed(card, result_language, master_duel_limit_regulation, should_exclude_icons(interaction))
                reply = await interaction.followup.send(embed=embeds[0] if len(embeds) == 1 else None, embeds=embeds if len(embeds) > 1 else None)
                await reply_latency(reply, interaction)

        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /search] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="search")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_search(self, ctx: commands.Context, *, term: str):
        """Commande préfixe pour rechercher une carte."""
        try:
            search_options = await get_card_search_options(ctx)
            type_, input_, result_language, input_language = (
                search_options['type'],
                search_options['input'],
                search_options['result_language'],
                search_options['input_language']
            )

            card = await get_card(type_, input_, input_language)
            if not card:
                use_locale(result_language)
                await safe_send(ctx.channel, f"❌ Could not find a card matching `{input_}`!")
            else:
                embeds = create_card_embed(card, result_language, master_duel_limit_regulation, should_exclude_icons(ctx))
                await safe_send(ctx.channel, embed=embeds[0] if len(embeds) == 1 else None, embeds=embeds if len(embeds) > 1 else None)

        except commands.CommandOnCooldown as e:
            await safe_send(ctx.channel, f"⏳ Attends encore {e.retry_after:.1f}s.")
        except Exception as e:
            print(f"[ERREUR !search] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = SearchCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
