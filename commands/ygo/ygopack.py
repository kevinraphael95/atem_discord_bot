# ================================================================================
# 📌 packopening.py
# Objectif : Ouvrir un booster Yu-Gi-Oh! aléatoire ou spécifique via l'API YGOPRODeck
# Catégorie : Fun / Jeux
# Accès : Tous
# Cooldown : 5 secondes par utilisateur
# Version optimisée : cache 1h + safe_defer + safe_followup + safe_edit_original
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import random
import time

from utils.discord_utils import (
    safe_send,
    safe_defer,
    safe_followup,
    safe_edit_original,
)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class PackOpening(commands.Cog):
    """Commande /ygopack et !ygopack — Ouvre un booster de cartes Yu-Gi-Oh!"""

    CACHE_TTL = 3600  # 1h pour la liste des sets

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._sets_cache = None
        self._sets_cache_time = 0

    # ============================================================================
    # 🔹 Récupération des sets (avec cache 1h)
    # ============================================================================
    async def _get_sets(self):
        """Récupère la liste des sets avec cache 1h."""
        now = time.monotonic()
        if self._sets_cache and (now - self._sets_cache_time) < self.CACHE_TTL:
            return self._sets_cache

        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return None

        try:
            async with session.get("https://db.ygoprodeck.com/api/v7/cardsets.php") as resp:
                if resp.status != 200:
                    return None
                self._sets_cache = await resp.json()
                self._sets_cache_time = now
                return self._sets_cache
        except Exception as e:
            print(f"[packopening] Erreur sets : {e}")
            return None

    # ============================================================================
    # 🔹 Fonction interne pour tirer un booster
    # ============================================================================
    async def _open_booster(self, set_query: str = None, num_cards: int = 5):
        """Ouvre un booster et retourne un embed (ou une erreur)."""
        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return None, "❌ Session HTTP non disponible."

        # 1. Liste des sets (avec cache)
        sets_data = await self._get_sets()
        if not sets_data:
            return None, "❌ Impossible de récupérer les boosters."

        # 2. Choix du set
        if set_query:
            set_query_lower = set_query.lower()
            matching_sets = [
                s for s in sets_data
                if set_query_lower == s.get("set_code", "").lower()
                or set_query_lower in s.get("set_name", "").lower()
            ]
            if not matching_sets:
                return None, f"❌ Aucun set trouvé pour **{set_query}**."
            chosen_set = matching_sets[0]
        else:
            chosen_set = random.choice(sets_data)

        set_name = chosen_set["set_name"]

        # 3. Récupère les cartes du set (1 appel API)
        params = {"cardset": set_name, "language": "fr"}
        try:
            async with session.get(
                "https://db.ygoprodeck.com/api/v7/cardinfo.php",
                params=params
            ) as resp:
                if resp.status != 200:
                    return None, f"❌ Impossible de récupérer les cartes du set **{set_name}**."
                cards_data = await resp.json()
        except Exception as e:
            print(f"[packopening] Erreur cards : {e}")
            return None, "❌ Erreur lors de la récupération du set."

        cards = cards_data.get("data", [])
        if not cards:
            return None, f"❌ Aucun résultat pour le set **{set_name}**."

        # 4. Tirage aléatoire
        pulled_cards = random.sample(cards, min(num_cards, len(cards)))

        # 5. Création de l'embed
        embed = discord.Embed(
            title=f"🎴 Booster ouvert : {set_name}",
            description=f"Voici les **{len(pulled_cards)}** cartes que tu as obtenues :",
            color=discord.Color.gold()
        )

        first_card = pulled_cards[0]
        first_image = first_card.get("card_images", [{}])[0].get("image_url")
        if first_image:
            embed.set_image(url=first_image)

        for card in pulled_cards:
            nom = card.get("name", "Carte inconnue")
            type_ = card.get("type", "Type inconnu")
            desc = card.get("desc", "Pas de description.")
            embed.add_field(
                name=f"**{nom}** — *{type_}*",
                value=desc[:150] + ("..." if len(desc) > 150 else ""),
                inline=False
            )

        embed.set_footer(text=f"Set code : {chosen_set.get('set_code', 'N/A')} • {len(cards)} cartes dans le set")

        return embed, None

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ygopack",
        description="Ouvre un booster de cartes Yu-Gi-Oh! (optionnel : nom du set et nombre de cartes)"
    )
    @app_commands.describe(
        set_name="Nom ou code du booster (facultatif)",
        cards="Nombre de cartes à tirer (max 10, défaut 5)"
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_packopening(self, interaction: discord.Interaction, set_name: str = None, cards: int = 5):
        # ✅ Defer sécurisé
        if not await safe_defer(interaction):
            return

        cards = max(1, min(cards, 10))
        embed, error = await self._open_booster(set_name, cards)

        if error:
            await safe_followup(interaction, error, ephemeral=True)
        else:
            await safe_edit_original(interaction, embed=embed)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="ygopack", aliases=["ypack"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_packopening(self, ctx: commands.Context, *, args: str = None):
        """Usage : !ygopack <nom du set> [nombre de cartes]"""
        num_cards = 5
        set_name = None

        if args:
            parts = args.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                set_name = parts[0]
                num_cards = max(1, min(int(parts[1]), 10))
            else:
                set_name = args

        embed, error = await self._open_booster(set_name, num_cards)
        if error:
            await safe_send(ctx, error)
        else:
            await safe_send(ctx, embed=embed)

# ================================================================================
# 🔌 Setup
# ================================================================================
async def setup(bot: commands.Bot):
    cog = PackOpening(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
