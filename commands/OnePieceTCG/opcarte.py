# ================================================================================
# 📌 opcarte.py — Commande /opcarte et !opcarte
# Objectif : Affiche une carte One Piece TCG via OPTCG API
# Catégorie : OnePieceTCG
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Version optimisée : safe_defer + cache 1h + session partagée
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import random
import time

from utils.discord_utils import safe_send, safe_defer, safe_followup, safe_edit_original

# ================================================================================
# 🌐 Constantes API
# ================================================================================
OPTCG_API_ALL = "https://www.optcgapi.com/api/allSetCards"

HEADERS = {
    "User-Agent": "VaactOPTCGBot/1.0",
    "Accept": "application/json"
}

CACHE_TTL = 3600  # 1h — la liste des cartes OP change rarement

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class OPCarte(commands.Cog):
    """Commande /opcarte et !opcarte — Affiche une carte One Piece TCG"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cards_cache = None
        self._cards_cache_time = 0

    # ============================================================================
    # 🔹 Utilitaire API (avec cache 1h)
    # ============================================================================
    async def _get_all_cards(self):
        """Récupère la liste complète des cartes avec cache 1h."""
        now = time.monotonic()
        if self._cards_cache and (now - self._cards_cache_time) < CACHE_TTL:
            return self._cards_cache

        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return None

        try:
            async with session.get(OPTCG_API_ALL, headers=HEADERS) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data:
                    return None
                self._cards_cache = data
                self._cards_cache_time = now
                return data
        except Exception as e:
            print(f"[opcarte] Erreur fetch : {e}")
            return None

    async def fetch_card(self, name: str | None = None) -> dict | None:
        """Récupère une carte One Piece par nom ou aléatoire."""
        data = await self._get_all_cards()
        if not data:
            return None

        if name:
            matches = [c for c in data if name.lower() in c.get("card_name", "").lower()]
            if matches:
                return random.choice(matches)
            return None  # Nom non trouvé → None (pas de fallback random)
        return random.choice(data)

    # ============================================================================
    # 🔹 Création de l'embed carte
    # ============================================================================
    def build_card_embed(self, card: dict) -> discord.Embed:
        name = card.get("card_name", "Carte inconnue")
        set_name = card.get("set_name", "—")
        set_id = card.get("set_id", "—")
        cost = card.get("card_cost", "—")
        power = card.get("card_power", "—")
        card_type = card.get("card_type", "—")
        sub_types = card.get("sub_types", "—")
        rarity = card.get("rarity", "—")
        attribute = card.get("attribute", "—")
        text = card.get("card_text") or "Pas de texte disponible."
        image = card.get("card_image")

        embed = discord.Embed(
            title=name,
            description=text,
            color=discord.Color.blue()
        )

        embed.add_field(name="Type", value=card_type, inline=True)
        embed.add_field(name="Sous-type", value=sub_types, inline=True)
        embed.add_field(name="Attribut", value=attribute, inline=True)
        embed.add_field(name="Coût", value=cost, inline=True)
        embed.add_field(name="Puissance", value=power, inline=True)
        embed.add_field(name="Rareté", value=rarity, inline=True)
        embed.add_field(name="Set", value=f"{set_name} ({set_id})", inline=True)

        if image:
            embed.set_image(url=image)

        embed.set_footer(text="💭 Source : OPTCG API")
        return embed

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="opcarte",
        description="Affiche une carte One Piece TCG (aléatoire si aucun nom)"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_opcarte(
        self,
        interaction: discord.Interaction,
        nom: str | None = None
    ):
        # ✅ Defer sécurisé
        if not await safe_defer(interaction):
            return

        card = await self.fetch_card(nom)
        if not card:
            return await safe_followup(
                interaction,
                f"❌ Carte `{nom}` introuvable." if nom else "❌ Impossible de récupérer une carte.",
                ephemeral=True
            )

        embed = self.build_card_embed(card)
        await safe_edit_original(interaction, embed=embed)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="opcarte", help="Affiche une carte One Piece TCG (aléatoire si aucun nom)")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_opcarte(self, ctx: commands.Context, *, nom: str | None = None):
        card = await self.fetch_card(nom)
        if not card:
            await safe_send(
                ctx.channel,
                f"❌ Carte `{nom}` introuvable." if nom else "❌ Impossible de récupérer une carte."
            )
            return
        embed = self.build_card_embed(card)
        await safe_send(ctx.channel, embed=embed)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = OPCarte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "OnePieceTCG"
    await bot.add_cog(cog)
