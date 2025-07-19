# ────────────────────────────────────────────────────────────────────────────────
# 📌 packopening.py — Commande !packopening
# Objectif : Ouvrir un booster aléatoire de Yu-Gi-Oh! et afficher les cartes obtenues (en français)
# Catégorie : Yu-Gi-Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import random
from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class PackOpeningCog(commands.Cog):
    """Commande !packopening — Ouvre un booster aléatoire de cartes Yu-Gi-Oh! (en français)"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="packopening", aliases=["pack"], help="Ouvre un booster aléatoire de Yu-Gi-Oh! (cartes en français)")
    async def packopening(self, ctx):
        """Ouvre un pack aléatoire via l'API YGOPRODeck avec noms en français."""
        try:
            async with aiohttp.ClientSession() as session:
                # 🔹 1. Récupération des sets disponibles
                async with session.get("https://db.ygoprodeck.com/api/v7/cardsets.php") as resp:
                    sets_data = await resp.json()

                if not sets_data:
                    return await safe_send(ctx, "❌ Impossible de récupérer les boosters.")

                # 🔹 2. Choix aléatoire d’un set
                chosen_set = random.choice(sets_data)
                set_name = chosen_set["set_name"]

                # 🔹 3. Récupération des cartes du set en FR
                params = {
                    "cardset": set_name,
                    "language": "fr"
                }
                async with session.get("https://db.ygoprodeck.com/api/v7/cardinfo.php", params=params) as resp:
                    cards_data = await resp.json()

                cards = cards_data.get("data", [])
                if not cards:
                    return await safe_send(ctx, f"❌ Aucun résultat pour le set **{set_name}**.")

                pulled_cards = random.sample(cards, min(5, len(cards)))

                # 🔹 4. Embed d'affichage
                embed = discord.Embed(
                    title=f"🎴 Booster ouvert : {set_name}",
                    description="Voici les cartes que tu as obtenues (🇫🇷 en français) :",
                    color=discord.Color.gold()
                )

                for card in pulled_cards:
                    nom = card.get('name', 'Carte inconnue')
                    type_ = card.get('type', 'Type inconnu')
                    desc = card.get('desc', 'Pas de description.')
                    embed.add_field(name=f"**{nom}** — *{type_}*", value=desc[:150] + "..." if len(desc) > 150 else desc, inline=False)

                await safe_send(ctx, embed=embed)

        except Exception as e:
            print(f"[ERREUR packopening] {e}")
            await safe_send(ctx, "❌ Une erreur est survenue lors de l'ouverture du pack.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot):
    cog = PackOpeningCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
