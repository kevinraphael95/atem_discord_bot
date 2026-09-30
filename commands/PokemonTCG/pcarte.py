# =============================================================
# 📌 pcarte.py — Commande Pokémon TCG
# Objectif : Afficher une carte Pokémon (ou random)
# Catégorie : 🃏 Pokémon TCG
# Accès : Public
# Cooldown : 1 / 3 sec
# Version optimisée : safe_defer + session partagée
# =============================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import random

from utils.discord_utils import safe_send, safe_defer, safe_followup

BASE_URL = "https://api.tcgdex.net/v2/en"

# =============================================================
# 🧠 Cog principal
# =============================================================
class PokemonCarte(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =========================================================
    # 🔹 Fonction interne pour afficher une carte
    # =========================================================
    async def _show_card(self, channel, query: str | None):
        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return await safe_send(channel, "❌ Session HTTP non disponible.")

        try:
            # 🔀 Random
            if not query or query.lower() == "random":
                async with session.get(f"{BASE_URL}/cards") as r:
                    if r.status != 200:
                        return await safe_send(channel, "❌ Impossible de récupérer une carte.")
                    data = await r.json()
                    card = random.choice(data) if data else None

            # 🆔 ID direct
            elif "-" in query:
                async with session.get(f"{BASE_URL}/cards/{query}") as r:
                    if r.status != 200:
                        return await safe_send(channel, "❌ Carte introuvable.")
                    card = await r.json()

            # 🔍 Recherche par nom
            else:
                async with session.get(f"{BASE_URL}/cards", params={"name": query}) as r:
                    if r.status != 200:
                        return await safe_send(channel, "❌ Carte introuvable.")
                    data = await r.json()
                    card = random.choice(data) if data else None
        except Exception as e:
            print(f"[pcarte] Erreur fetch : {e}")
            return await safe_send(channel, "❌ Une erreur est survenue.")

        if not card:
            return await safe_send(channel, "❌ Carte introuvable.")

        # ===============
        # 📊 Infos carte
        # ===============
        name = card.get("name", "Carte inconnue")
        hp = card.get("hp")
        types = card.get("types", [])
        rarity = card.get("rarity", "Inconnue")
        image = card.get("image")
        set_data = card.get("set", {})
        attacks = card.get("attacks", [])
        evolve_from = card.get("evolveFrom")

        desc_lines = []

        if hp:
            desc_lines.append(f"❤️ **HP** : {hp}")
        if types:
            desc_lines.append(f"🔮 **Type(s)** : {', '.join(types)}")
        if rarity:
            desc_lines.append(f"💎 **Rareté** : {rarity}")
        if set_data:
            desc_lines.append(f"📦 **Set** : {set_data.get('name')}")
        if evolve_from:
            desc_lines.append(f"🔼 **Évolue de** : {evolve_from}")

        if attacks:
            attack_lines = []
            for atk in attacks:
                name_atk = atk.get("name")
                effect = atk.get("effect")
                damage = atk.get("damage")
                line = f"**{name_atk}**"
                if damage: line += f" ({damage} dmg)"
                if effect: line += f" → {effect}"
                attack_lines.append(line)
            desc_lines.append("⚔️ **Attaques** :\n" + "\n".join(attack_lines))

        embed = discord.Embed(
            title=name,
            description="\n".join(desc_lines),
            color=discord.Color.red()
        )

        if image:
            embed.set_thumbnail(url=f"{image}/high.png")

        await safe_send(channel, embed=embed)

    # =========================================================
    # 🔹 Slash command
    # =========================================================
    @app_commands.command(
        name="pcarte",
        description="Afficher une carte Pokémon TCG (ou random)."
    )
    @app_commands.describe(nom="Nom, ID (ex: swsh3-136) ou 'random'")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_pcarte(self, interaction: discord.Interaction, nom: str = None):
        # ✅ Defer sécurisé
        if not await safe_defer(interaction):
            return
        await self._show_card(interaction.channel, nom)
        # Pas de delete, defer = invisible

    # =========================================================
    # 🔹 Prefix command
    # =========================================================
    @commands.command(name="pcarte", aliases=["pokemon"], help="Afficher une carte Pokémon TCG (ou random).")
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_pcarte(self, ctx: commands.Context, *, nom: str = None):
        await self._show_card(ctx.channel, nom)

# =============================================================
# 🔌 Setup du Cog
# =============================================================
async def setup(bot: commands.Bot):
    cog = PokemonCarte(bot)
    for cmd in cog.get_commands():
        if not hasattr(cmd, "category"):
            cmd.category = "PokemonTCG"
    await bot.add_cog(cog)
