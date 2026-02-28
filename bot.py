# ────────────────────────────────────────────────────────────────────────────────
# 📌 bot.py — Script principal du bot Discord
# Objectif : Initialisation, gestion des commandes et événements du bot
# Catégorie : Général
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules standards
# ────────────────────────────────────────────────────────────────────────────────
import os
import json
import uuid
import random
from datetime import datetime, timezone
import asyncio
import atexit

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules tiers
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from dotenv import load_dotenv
from dateutil import parser
import aiohttp

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules internes
# ────────────────────────────────────────────────────────────────────────────────
from utils.discord_utils import safe_send  # ✅ Utilitaires anti-429
from utils.init_db import init_db          # <-- IMPORT INIT_DB

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Initialisation de l’environnement
# ────────────────────────────────────────────────────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "%")
INSTANCE_ID = str(uuid.uuid4())

with open("instance_id.txt", "w") as f:
    f.write(INSTANCE_ID)

def get_prefix(bot, message):
    return COMMAND_PREFIX

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Initialisation des bases SQLite locales
# ────────────────────────────────────────────────────────────────────────────────
init_db()  # <-- ici on crée tournoi.db et profil.db si elles n'existent pas
print("✅ Bases SQLite prêtes")

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Intents & Création du bot
# ────────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.guild_reactions = True
intents.dm_reactions = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
bot.INSTANCE_ID = INSTANCE_ID
bot.aiohttp_session = None  # sera initialisée plus tard

# ────────────────────────────────────────────────────────────────────────────────
# 🔒 Nettoyage aiohttp
# ────────────────────────────────────────────────────────────────────────────────
async def cleanup_aiohttp():
    if bot.aiohttp_session and not bot.aiohttp_session.closed:
        await bot.aiohttp_session.close()

atexit.register(lambda: asyncio.run(cleanup_aiohttp()))

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Chargement dynamique des commandes depuis /commands/*
# ────────────────────────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Chargement dynamique des tasks depuis /tasks/*
# ────────────────────────────────────────────────────────────────────────────────
async def load_tasks():
    for filename in os.listdir("tasks"):
        if filename.endswith(".py") and filename != "__init__.py":
            path = f"tasks.{filename[:-3]}"
            try:
                await bot.load_extension(path)
                print(f"✅ Task loaded: {path}")
            except Exception as e:
                print(f"❌ Failed to load task {path}: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔔 On Ready : présence et création de session aiohttp
# ────────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    if bot.aiohttp_session is None:
        bot.aiohttp_session = aiohttp.ClientSession()  # ✅ Créée dans le loop
    print(f"✅ Connecté en tant que {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Duel Monsters"))

# ────────────────────────────────────────────────────────────────────────────────
# 📩 Message reçu : réagir aux mots-clés et lancer les commandes
# ────────────────────────────────────────────────────────────────────────────────
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

        await safe_send(message.channel, embed=embed)
        return

    await bot.process_commands(message)

# ────────────────────────────────────────────────────────────────────────────────
# ❗ Gestion des erreurs de commandes
# ────────────────────────────────────────────────────────────────────────────────
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
        raise error

# ────────────────────────────────────────────────────────────────────────────────
# 🚀 Lancement
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    async def start():
        await load_commands()
        await load_tasks()
        await bot.start(TOKEN)

    asyncio.run(start())



