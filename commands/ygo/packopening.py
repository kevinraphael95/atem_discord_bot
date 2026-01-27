# ────────────────────────────────────────────────────────────────────────────────
# 📌 packopening.py
# Objectif : Ouvrir un booster Yu-Gi-Oh! aléatoire ou spécifique via l'API YGOPRODeck
# Catégorie : Fun / Jeux
# Accès : Tous
# Cooldown : 5 secondes par utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View
import aiohttp
import random

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class PackOpening(commands.Cog):
    """
    Commande /packopening et !packopening — Ouvre un booster de cartes Yu-Gi-Oh!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour tirer un booster
    # ────────────────────────────────────────────────────────────────────────────
    async def _open_booster(self, set_query: str = None, num_cards: int = 5):
        """
        Récupère les cartes depuis YGOPRODeck et retourne un embed Discord.
        """
        async with aiohttp.ClientSession() as session:
            # Récupère tous les sets
            async with session.get("https://db.ygoprodeck.com/api/v7/cardsets.php") as resp:
                sets_data = await resp.json()

            if not sets_data:
                return None, "❌ Impossible de récupérer les boosters."

            # Choix du set
            if set_query:
                set_query_lower = set_query.lower()
                matching_sets = [
                    s for s in sets_data
                    if set_query_lower == s["set_code"].lower() or set_query_lower in s["set_name"].lower()
                ]
                if not matching_sets:
                    return None, f"❌ Aucun set trouvé pour **{set_query}**."
                chosen_set = matching_sets[0]
            else:
                chosen_set = random.choice(sets_data)

            set_name = chosen_set["set_name"]

            # Récupère les cartes du set en français
            params = {"cardset": set_name, "language": "fr"}
            async with session.get("https://db.ygoprodeck.com/api/v7/cardinfo.php", params=params) as resp:
                cards_data = await resp.json()

            cards = cards_data.get("data", [])
            if not cards:
                return None, f"❌ Aucun résultat pour le set **{set_name}**."

            # Tirage aléatoire
            pulled_cards = random.sample(cards, min(num_cards, len(cards)))

            # Création de l'embed
            embed = discord.Embed(
                title=f"🎴 Booster ouvert : {set_name}",
                description="Voici les cartes que tu as obtenues :",
                color=discord.Color.gold()
            )

            for card in pulled_cards:
                nom = card.get('name', 'Carte inconnue')
                type_ = card.get('type', 'Type inconnu')
                desc = card.get('desc', 'Pas de description.')
                image_url = card.get("card_images", [{}])[0].get("image_url", None)
                embed.add_field(
                    name=f"**{nom}** — *{type_}*",
                    value=desc[:150] + "..." if len(desc) > 150 else desc,
                    inline=False
                )
                if image_url:
                    embed.set_thumbnail(url=image_url)

            return embed, None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="packopening",
        description="Ouvre un booster de cartes Yu-Gi-Oh! (optionnel : nom du set et nombre de cartes)"
    )
    @app_commands.describe(
        set_name="Nom ou code du booster (facultatif)",
        cards="Nombre de cartes à tirer (max 10, défaut 5)"
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_packopening(self, interaction: discord.Interaction, set_name: str = None, cards: int = 5):
        await interaction.response.defer()
        cards = max(1, min(cards, 10))  # Limite de 1 à 10 cartes
        embed, error = await self._open_booster(set_name, cards)
        if error:
            await safe_send(interaction.channel, error)
        else:
            await safe_send(interaction.channel, embed=embed)
        await interaction.delete_original_response()

    
    # ────────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────────
    @commands.command(name="packopening", aliases=["pack"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_packopening(self, ctx: commands.Context, *, args: str = None):
        """
        !packopening <nom du set> [nombre de cartes]
        Exemple : !packopening Legend of Blue Eyes White Dragon 5
        """
        num_cards = 5  # valeur par défaut
        set_name = None
    
        if args:
            # Vérifie si le dernier mot est un nombre pour le nombre de cartes
            parts = args.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                set_name = parts[0]
                num_cards = max(1, min(int(parts[1]), 10))  # limite de 1 à 10 cartes
            else:
                set_name = args
    
        embed, error = await self._open_booster(set_name, num_cards)
        if error:
            await safe_send(ctx, error)
        else:
            await safe_send(ctx, embed=embed)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot):
    cog = PackOpening(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
