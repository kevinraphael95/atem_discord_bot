# ────────────────────────────────────────────────────────────────────────────────
# 🎲 Random.py — Commande !random
# Objectif : Tirer une carte Yu-Gi-Oh! aléatoire et l'afficher joliment dans un embed
# Source : API publique YGOPRODeck (https://db.ygoprodeck.com/api-guide/)
# Langue : 🇫🇷 Français uniquement
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord                                 # Outils pour embeds Discord
from discord.ext import commands              # Gestion des commandes dans un Cog
import aiohttp                                 # Requêtes HTTP asynchrones
import random                                  # Sélection aléatoire

# ────────────────────────────────────────────────────────────────────────────────
# 📘 Classe principale du Cog de commande !random
# ────────────────────────────────────────────────────────────────────────────────
class Random(commands.Cog):
    """
    🎲 Cog de la commande !random : tire une carte Yu-Gi-Oh! aléatoire via l'API officielle.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot  # 🔗 Référence au bot principal

    # ────────────────────────────────────────────────────────────────────────────
    # 🎯 Commande principale !random
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="random", aliases=["aléatoire", "ran"], help="Affiche une carte Yu-Gi-Oh! aléatoire.")
    @commands.cooldown(1, 5, commands.BucketType.user)  # ⏱️ 1 utilisation toutes les 5s par utilisateur
    async def random_card(self, ctx: commands.Context):
        """
        📥 Récupère une carte Yu-Gi-Oh! aléatoire depuis l’API (langue : français)
        et l'affiche joliment dans un embed Discord.
        """

        # ────────────────────────────────────────────────────────────────────────
        # 🔗 Requête API vers la base de cartes Yu-Gi-Oh! (langue française)
        # ────────────────────────────────────────────────────────────────────────
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await ctx.send("❌ Erreur lors de l'accès à l'API.")
                    return
                data = await resp.json()

        # 🔍 Vérification des données renvoyées
        if "data" not in data:
            await ctx.send("❌ Données invalides reçues depuis l’API.")
            return

        # 🎯 Tirage d’une carte au hasard parmi toutes celles disponibles
        carte = random.choice(data["data"])

        # ────────────────────────────────────────────────────────────────────────
        # 🖼️ Création de l’embed de réponse avec les infos de la carte
        # ────────────────────────────────────────────────────────────────────────
        embed = discord.Embed(
            title=carte["name"],  # 🏷️ Nom de la carte
            description=carte.get("desc", "Pas de description disponible."),  # 📖 Description de la carte
            color=discord.Color.gold()  # 🎨 Couleur dorée
        )

        embed.set_author(
            name="Carte aléatoire Yu-Gi-Oh!",
            icon_url="https://cdn-icons-png.flaticon.com/512/361/361678.png"
        )

        # ➕ Champ : Type de la carte (ex : Monstre, Magie, Piège)
        embed.add_field(name="🧪 Type", value=carte.get("type", "—"), inline=True)

        # 📊 Si c’est une carte Monstre, ajouter ses stats complémentaires
        if carte.get("type", "").lower().startswith("monstre"):
            embed.add_field(
                name="⚔️ ATK / DEF",
                value=f"{carte.get('atk', '—')} / {carte.get('def', '—')}",
                inline=True
            )
            embed.add_field(
                name="⭐ Niveau / Rang",
                value=str(carte.get("level", "—")),
                inline=True
            )
            embed.add_field(
                name="🌪️ Attribut",
                value=carte.get("attribute", "—"),
                inline=True
            )
            embed.add_field(
                name="👹 Race",
                value=carte.get("race", "—"),
                inline=True
            )

        # 🖼️ Image de la carte (miniature)
        image_url = carte.get("card_images", [{}])[0].get("image_url")
        if image_url:
            embed.set_thumbnail(url=image_url)

        # 📤 Envoi final de l’embed dans le salon
        await ctx.send(embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Fonction de setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    """
    🔧 Fonction appelée par Discord pour charger le Cog dans le bot.
    Permet d’ajouter les commandes dans la catégorie "🃏 Yu-Gi-Oh!".
    """
    cog = Random(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"  # Organisation dans l’aide du bot
    await bot.add_cog(cog)
