# ────────────────────────────────────────────────────────────────────────────────
# 📌 discord_utils.py — Fonctions utilitaires avec gestion du rate-limit
# Objectif : Fournir des fonctions sécurisées pour send/edit/respond Discord
# Catégorie : Général
# Accès : Public (utilisable dans tous les Cogs)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import asyncio
import discord
from discord.errors import HTTPException

# ────────────────────────────────────────────────────────────────────────────────
# 🛡️ Fonctions sécurisées pour Discord
# ────────────────────────────────────────────────────────────────────────────────

async def safe_send(channel: discord.TextChannel, content=None, **kwargs):
    """
    Envoie un message sur un channel Discord avec gestion du rate-limit (429).
    """
    try:
        return await channel.send(content=content, **kwargs)
    except HTTPException as e:
        if e.status == 429:
            print("[RateLimit] safe_send() → 429 Too Many Requests. Pause...")
            await asyncio.sleep(10)
            return await channel.send(content=content, **kwargs)
        raise e

async def safe_edit(message: discord.Message, content=None, **kwargs):
    """
    Modifie un message Discord avec gestion du rate-limit (429).
    """
    try:
        return await message.edit(content=content, **kwargs)
    except HTTPException as e:
        if e.status == 429:
            print("[RateLimit] safe_edit() → 429 Too Many Requests. Pause...")
            await asyncio.sleep(10)
            return await message.edit(content=content, **kwargs)
        raise e

async def safe_respond(interaction: discord.Interaction, content=None, **kwargs):
    """
    Répond à une interaction avec gestion du rate-limit (429).
    """
    try:
        return await interaction.response.send_message(content=content, **kwargs)
    except HTTPException as e:
        if e.status == 429:
            print("[RateLimit] safe_respond() → 429 Too Many Requests. Pause...")
            await asyncio.sleep(10)
            return await interaction.response.send_message(content=content, **kwargs)
        raise e

async def safe_reply(ctx_or_message, content=None, **kwargs):
    """
    Répond à un message ou un contexte Discord avec gestion du rate-limit (429).
    """
    try:
        return await ctx_or_message.reply(content=content, **kwargs)
    except HTTPException as e:
        if e.status == 429:
            print("[RateLimit] safe_reply() → 429 Too Many Requests. Pause...")
            await asyncio.sleep(10)
            return await ctx_or_message.reply(content=content, **kwargs)
        raise e
