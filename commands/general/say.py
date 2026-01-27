# ────────────────────────────────────────────────────────────────────────────────
# 📌 say.py — Commande interactive /say et !say
# Objectif : Faire répéter un message par le bot, avec options combinables (*embed, *as_me, ...)
# Catégorie : Général
# Accès : Public
# Cooldown : 5s / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import re
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_delete, safe_respond  

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Say(commands.Cog):
    """Commande /say et !say — Faire répéter un message par le bot, avec options modulables."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ──────────────────────────────────────────────────────────────
    async def _say(self, channel: discord.abc.Messageable, user: discord.User, message: str, embed: bool = False, as_user: bool = False):
        """Envoie un message normal ou via webhook selon as_user."""
        if not message:
            return
        message = self._replace_custom_emojis(channel, message)
        if len(message) > 2000:
            message = message[:1997] + "..."
        if as_user:
            webhook = await channel.create_webhook(name=f"tmp-{user.name}")
            try:
                if embed:
                    embed_obj = discord.Embed(description=message, color=discord.Color.blurple())
                    await webhook.send(username=user.display_name, avatar_url=user.display_avatar.url, embed=embed_obj)
                else:
                    await webhook.send(username=user.display_name, avatar_url=user.display_avatar.url, content=message)
            finally:
                await webhook.delete()
        else:
            if embed:
                embed_obj = discord.Embed(description=message, color=discord.Color.blurple())
                await safe_send(channel, embed=embed_obj, allowed_mentions=discord.AllowedMentions.none())
            else:
                await safe_send(channel, message, allowed_mentions=discord.AllowedMentions.none())

    # ──────────────────────────────────────────────────────────────
    # 🔹 Remplacement emojis custom
    # ──────────────────────────────────────────────────────────────
    def _replace_custom_emojis(self, channel, message: str) -> str:
        if hasattr(channel, "guild"):
            guild_emojis = {e.name.lower(): str(e) for e in channel.guild.emojis}
            return re.sub(
                r":([a-zA-Z0-9_]+):",
                lambda m: guild_emojis.get(m.group(1).lower(), m.group(0)),
                message,
                flags=re.IGNORECASE
            )
        return message

    # ──────────────────────────────────────────────────────────────
    # 🔹 Parsing des options (pour prefix)
    # ──────────────────────────────────────────────────────────────
    def _parse_options(self, raw_message: str):
        options = {"embed": False, "as_user": False}
        opts_pattern = r"^(?:\*(embed|e|as_me|am|me)\s*)+"
        match = re.match(opts_pattern, raw_message, re.IGNORECASE)
        if match:
            opts_part = match.group()
            if re.search(r"\*(embed|e)\b", opts_part, re.IGNORECASE):
                options["embed"] = True
            if re.search(r"\*(as_me|am|me)\b", opts_part, re.IGNORECASE):
                options["as_user"] = True
            raw_message = raw_message[len(opts_part):]
        return options, raw_message

    # ──────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ──────────────────────────────────────────────────────────────
    @app_commands.command(
        name="say",
        description="Fait répéter un message par le bot, avec options combinables (*embed, *as_me, ...)."
    )
    @app_commands.describe(
        message="Message à répéter",
        embed="Envoyer dans un embed",
        as_user="Parler comme vous"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_say(self, interaction: discord.Interaction, message: str, embed: bool = False, as_user: bool = False):
        try:
            await interaction.response.defer()
            await self._say(interaction.channel, interaction.user, message, embed, as_user)
            await safe_respond(interaction, "✅ Message envoyé !", ephemeral=True)
            await interaction.delete_original_response()
        except Exception as e:
            print(f"[ERREUR /say] {e}")
            await safe_respond(interaction, "❌ Impossible d’envoyer le message.", ephemeral=True)

    # ──────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ──────────────────────────────────────────────────────────────
    @commands.command(
        name="say",
        help="Fait répéter un message par le bot. Options : *embed / *e, *as_me / *am. Ex: !say *e *am Bonjour !"
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_say(self, ctx: commands.Context, *, message: str):
        try:
            options, clean_message = self._parse_options(message)
            await self._say(ctx.channel, ctx.author, clean_message, options["embed"], options["as_user"])
        except Exception as e:
            print(f"[ERREUR !say] {e}")
            await safe_send(ctx.channel, "❌ Impossible d’envoyer le message.")
        finally:
            await safe_delete(ctx.message)

# ──────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ──────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Say(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
