# ────────────────────────────────────────────────────────────────────────────────
# 📌 say.py — Commande interactive /say et !say
# Objectif : Faire répéter un message par le bot (texte ou embed)
# Catégorie : Général
# Accès : Public
# Cooldown : 1 utilisation / 5 sec / utilisateur
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
    """Commande interactive /say et !say — Faire répéter un message par le bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne
    # ────────────────────────────────────────────────────────────────────────────
    async def _say_message(self, channel: discord.abc.Messageable, message: str, embed: bool = False):
        """Envoie un message formaté avec tous les emojis custom remplacés efficacement (case-insensible)."""
        message = (message or "").strip()
        if not message:
            return await safe_send(channel, "⚠️ Message vide.")

        pattern = r":([a-zA-Z0-9_]+):"

        if hasattr(channel, "guild"):  # On est dans un serveur
            # dictionnaire en lowercase pour éviter les soucis de majuscules
            guild_emojis = {e.name.lower(): str(e) for e in channel.guild.emojis}

            def replace_emoji(match):
                name = match.group(1).lower()
                return guild_emojis.get(name, match.group(0))  # garde le texte si emoji non trouvé

            message = re.sub(pattern, replace_emoji, message, flags=re.IGNORECASE)

        # ✂️ Limite de caractères Discord
        if len(message) > 2000:
            message = message[:1997] + "..."

        # 📤 Envoi final
        if embed:
            embed_obj = discord.Embed(
                description=message,
                color=discord.Color.blurple()
            )
            await safe_send(channel, embed=embed_obj, allowed_mentions=discord.AllowedMentions.none())
        else:
            await safe_send(channel, message, allowed_mentions=discord.AllowedMentions.none())



    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="say",
        description="Fait répéter un message par le bot."
    )
    @app_commands.describe(
        message="Message à répéter",
        embed="Envoyer le message dans un embed"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.user.id))
    async def slash_say(self, interaction: discord.Interaction, message: str, embed: bool = False):
        try:
            await self._say_message(interaction.channel, message, embed)
            await safe_respond(interaction, "✅ Message envoyé !", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /say] {e}")
            await safe_respond(interaction, "❌ Impossible d’envoyer le message.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="say",
        help="Fait répéter un message par le bot. Utilise `embed` au début pour forcer un embed."
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_say(self, ctx: commands.Context, *, message: str):
        embed = False
        if message.lower().startswith("embed "):
            embed = True
            message = message[6:]  # enlever le mot "embed"

        try:
            await self._say_message(ctx.channel, message, embed)
        except Exception as e:
            print(f"[ERREUR !say] {e}")
            await safe_send(ctx.channel, "❌ Impossible d’envoyer le message.")
        finally:
            await safe_delete(ctx.message)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Say(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
