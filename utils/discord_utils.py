# ────────────────────────────────────────────────────────────────────────────────
# 📌 discord_utils.py — Fonctions utilitaires sécurisées pour Discord
# Objectif : Fournir des fonctions send/edit/respond optimisées avec gestion du rate-limit
# Version : ✅ Optimisée et robuste, backoff exponentiel, logs clairs
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import asyncio
import discord
from discord.errors import HTTPException

# ────────────────────────────────────────────────────────────────────────────────
# 🛡️ Gestion centralisée des appels Discord avec backoff 429
# ────────────────────────────────────────────────────────────────────────────────
async def _discord_action(action_func, *args, retry: int = 3, delay: float = 0.3, timeout: float = 10, **kwargs):
    """
    Exécute une action Discord sécurisée avec gestion du rate-limit et des exceptions.
    - action_func : fonction Discord à appeler (send, edit, reply, etc.)
    - retry : nombre de tentatives en cas de 429
    - delay : délai entre chaque tentative (anti-429)
    - timeout : durée max avant abandon (seconds)
    """
    for attempt in range(1, retry + 2):
        try:
            return await asyncio.wait_for(action_func(*args, **kwargs), timeout=timeout)
        except HTTPException as e:
            if e.status == 429:
                wait_time = min(10 * attempt, 60)  # backoff exponentiel avec max 60s
                print(f"[RateLimit] {action_func.__name__} → 429 Too Many Requests. Pause {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"[Erreur HTTP] {action_func.__name__} → {e}")
                return None
        except asyncio.TimeoutError:
            print(f"[Timeout] {action_func.__name__} → Échec après {timeout}s")
            return None
        except Exception as e:
            print(f"[Erreur] {action_func.__name__} → {e}")
            return None
        if delay > 0:
            await asyncio.sleep(delay)
    print(f"[Échec] {action_func.__name__} → Échec après {retry+1} tentatives")
    return None

# ────────────────────────────────────────────────────────────────────────────────
# 📩 Fonctions publiques sécurisées
# ────────────────────────────────────────────────────────────────────────────────
async def safe_send(channel: discord.abc.Messageable, content=None, **kwargs):
    return await _discord_action(channel.send, content=content, **kwargs)

async def safe_edit(message: discord.Message, content=None, **kwargs):
    return await _discord_action(message.edit, content=content, **kwargs)

async def safe_respond(interaction: discord.Interaction, content=None, **kwargs):
    return await _discord_action(interaction.response.send_message, content=content, **kwargs)

async def safe_followup(interaction: discord.Interaction, content=None, **kwargs):
    return await _discord_action(interaction.followup.send, content=content, **kwargs)

async def safe_reply(ctx_or_message, content=None, **kwargs):
    return await _discord_action(ctx_or_message.reply, content=content, **kwargs)

async def safe_add_reaction(message: discord.Message, emoji: str, delay: float = 0.3):
    result = await _discord_action(message.add_reaction, emoji)
    if delay > 0:
        await asyncio.sleep(delay)
    return result

async def safe_delete(message: discord.Message, delay: float = 0):
    result = await _discord_action(message.delete)
    if delay > 0:
        await asyncio.sleep(delay)
    return result

async def safe_clear_reactions(message: discord.Message, delay: float = 0.3):
    result = await _discord_action(message.clear_reactions)
    if delay > 0:
        await asyncio.sleep(delay)
    return result
