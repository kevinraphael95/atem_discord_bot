# ================================================================================
# 📌 bot.py — Script principal du bot Discord (Atem / Yu-Gi-Oh)
# Objectif : Initialisation, gestion des commandes et événements du bot
# Catégorie : Général
# Accès : Public
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import os
import asyncio

# ================================================================================
# 📦 Modules tiers
# ================================================================================
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import aiohttp

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_utils import safe_send, safe_respond, safe_interact
from utils.init_db import init_db

# ================================================================================
# 🔧 Initialisation de l'environnement
# ================================================================================
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

TOKEN          = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "%")

GITHUB_URL = "https://github.com/kevinraphael95/atem_discord_bot"
SITE_URL   = "https://kevinraphael95.github.io/atem_discord_bot/index.html"

def get_prefix(bot, message):
    return COMMAND_PREFIX

# ================================================================================
# ⚙️ Intents & Création du bot
# ================================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.guild_reactions = True
intents.dm_reactions = True

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)
bot.aiohttp_session = None

# ================================================================================
# 🔌 Chargement dynamique des commandes
# ================================================================================
async def load_commands():
    for category in os.listdir("commands"):
        cat_path = os.path.join("commands", category)
        if os.path.isdir(cat_path):
            for filename in os.listdir(cat_path):
                if filename.endswith(".py") and filename != "__init__.py":
                    path = f"commands.{category}.{filename[:-3]}"
                    try:
                        await bot.load_extension(path)
                        print(f"✅ Loaded {path}")
                    except Exception as e:
                        print(f"❌ Failed to load {path}: {e}")

async def load_tasks():
    for filename in os.listdir("tasks"):
        if filename.endswith(".py") and filename != "__init__.py":
            path = f"tasks.{filename[:-3]}"
            try:
                await bot.load_extension(path)
                print(f"✅ Task loaded: {path}")
            except Exception as e:
                print(f"❌ Failed to load task {path}: {e}")

# ================================================================================
# 🔔 On Ready
# ================================================================================
@bot.event
async def on_ready():
    if bot.aiohttp_session is None:
        bot.aiohttp_session = aiohttp.ClientSession()
    print(f"✅ Connecté en tant que {bot.user.name}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="Duel Monsters"
        )
    )

# ================================================================================
# 📩 On Message
# ================================================================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.strip() in [f"<@!{bot.user.id}>", f"<@{bot.user.id}>"]:
        prefix = get_prefix(bot, message)
        embed = discord.Embed(
            title="Coucou ! 🃏",
            description=(
                f"Bonjour ! Je suis **Atem**, un bot discord inspiré du manga Yu-Gi-Oh.\n"
                f"• Utilise la commande `{prefix}help` pour avoir la liste des commandes du bot "
                f"ou `{prefix}help + le nom d'une commande` pour en avoir une description."
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="Tu dois croire en l'âme des cartes 🎴")

        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        else:
            embed.set_thumbnail(url=bot.user.default_avatar.url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🌐 Site", url=SITE_URL, style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="📂 Github", url=GITHUB_URL, style=discord.ButtonStyle.link))

        await safe_send(message.channel, embed=embed, view=view)
        return

    await bot.process_commands(message)

# ================================================================================
# ❗ Gestion des erreurs
# ================================================================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry = round(error.retry_after, 1)
        await safe_send(ctx.channel, f"⏳ Cette commande est en cooldown. Réessaie dans `{retry}` secondes.")
    elif isinstance(error, commands.MissingPermissions):
        await safe_send(ctx.channel, "❌ Tu n'as pas les permissions pour cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await safe_send(ctx.channel, "⚠️ Il manque un argument à cette commande.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await safe_interact(interaction, f"⏳ Attends encore {error.retry_after:.1f}s.", edit=True, ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await safe_interact(interaction, "❌ Tu n'as pas les permissions.", edit=True, ephemeral=True)
    else:
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)
        await safe_interact(interaction, "❌ Une erreur est survenue.", edit=True, ephemeral=True)

# ================================================================================
# 🔒 Nettoyage aiohttp
# ================================================================================
async def cleanup_aiohttp():
    if bot.aiohttp_session and not bot.aiohttp_session.closed:
        await bot.aiohttp_session.close()

# ================================================================================
# 🚀 Lancement
# ================================================================================
if __name__ == "__main__":
    async def start():
        init_db()
        await load_commands()
        await load_tasks()
        try:
            await bot.start(TOKEN)
        finally:
            await cleanup_aiohttp()

    asyncio.run(start())
