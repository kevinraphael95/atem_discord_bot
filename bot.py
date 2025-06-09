# ──────────────────────────────────────────────────────────────
# 🔄 Keep-Alive Render
# ──────────────────────────────────────────────────────────────
from keep_alive import keep_alive

# ──────────────────────────────────────────────────────────────
# 📦 Modules
# ──────────────────────────────────────────────────────────────
import os
import json
import uuid
import asyncio
import random
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from supabase_client import supabase  # Supabase client interne

# ──────────────────────────────────────────────────────────────
# ⚙️ Initialisation
# ──────────────────────────────────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
INSTANCE_ID = str(uuid.uuid4())

with open("instance_id.txt", "w") as f:
    f.write(INSTANCE_ID)

# ──────────────────────────────────────────────────────────────
# 🔧 Intents & Bot
# ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=lambda bot, msg: COMMAND_PREFIX, intents=intents, help_command=None)
bot.is_main_instance = False

# ──────────────────────────────────────────────────────────────
# 🔌 Chargement des commandes
# ──────────────────────────────────────────────────────────────
async def load_commands():
    for root, _, files in os.walk("commands"):
        for file in files:
            if file.endswith(".py"):
                module = os.path.join(root, file).replace("/", ".").replace("\\", ".").replace(".py", "")
                try:
                    await bot.load_extension(module)
                    print(f"✅ Commande chargée : {module}")
                except Exception as e:
                    print(f"❌ Erreur chargement {module} : {e}")

# ──────────────────────────────────────────────────────────────
# 🔐 Verrouillage Supabase
# ──────────────────────────────────────────────────────────────
async def acquire_lock():
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("bot_lock").delete().eq("id", "bot_lock").execute()
    supabase.table("bot_lock").insert({
        "id": "bot_lock",
        "instance_id": INSTANCE_ID,
        "updated_at": now
    }).execute()
    bot.is_main_instance = True
    print(f"🔐 Verrou acquis : {INSTANCE_ID}")

async def is_locked_by_us():
    res = supabase.table("bot_lock").select("instance_id").eq("id", "bot_lock").execute()
    if res.data and res.data[0]["instance_id"] == INSTANCE_ID:
        return True
    return False

# ──────────────────────────────────────────────────────────────
# 🟢 On Ready
# ──────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game("Yu-Gi-Oh Master Duel ⚔️"))
    await acquire_lock()

# ──────────────────────────────────────────────────────────────
# 📩 Message reçu
# ──────────────────────────────────────────────────────────────
@bot.event
async def on_message(message):
    if not await is_locked_by_us():
        return

    if message.author.bot:
        return

    await bot.process_commands(message)

# ──────────────────────────────────────────────────────────────
# ❗ Gestion des erreurs & anti-rate-limit
# ──────────────────────────────────────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry = round(error.retry_after, 1)
        await ctx.send(f"⏳ Commande en cooldown. Réessaie dans `{retry}` secondes.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        print(f"⚠️ Erreur : {error}")
        raise error

@bot.event
async def on_error(event_method, *args, **kwargs):
    print(f"❌ Erreur dans l’événement {event_method}")
    import traceback
    traceback.print_exc()

# Tâche de sécurité pour les limits
@tasks.loop(seconds=10)
async def ping_rate_limit_check():
    if bot.is_main_instance:
        try:
            await bot.application_info()  # ping soft à Discord
        except discord.HTTPException as e:
            if e.status == 429:
                print("🚨 Rate limit détecté ! Mise en pause...")
                await asyncio.sleep(30)

# ──────────────────────────────────────────────────────────────
# 🚀 Lancement
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    keep_alive()

    async def start():
        await load_commands()
        ping_rate_limit_check.start()
        await bot.start(TOKEN)

    asyncio.run(start())
