# ────────────────────────────────────────────────────────────────────────────────
# 📌 cartefav.py — Commande interactive !cartefav
# Objectif : Afficher les cartes favorites d’un utilisateur avec infos détaillées Yu-Gi-Oh!
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import urllib.parse
from utils.discord_utils import safe_send  # ✅ Utilisation des fonctions safe_
from utils.supabase_client import supabase        # Client Supabase déjà configuré

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CarteFav(commands.Cog):
    """
    Commande !cartefav — Affiche les cartes favorites d’un utilisateur Discord,
    avec une présentation simplifiée : message + image de la carte.
    Usage : !cartefav [@utilisateur]
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="cartefav",
        help="⭐ Affiche les cartes favorites de l’utilisateur mentionné ou de vous-même.",
        description="Affiche l’image des cartes favorites d’un utilisateur avec un message simple."
    )
    async def cartefav(self, ctx: commands.Context, user: discord.User = None):
        user = user or ctx.author
        user_id = str(user.id)

        try:
            # Récupérer toutes les cartes favorites de l’utilisateur
            response = supabase.table("profil").select("cartefav").eq("user_id", user_id).execute()
            cartes_data = response.data

            if not cartes_data:
                if user == ctx.author:
                    await safe_send(ctx.channel, "❌ Vous n’avez pas encore de carte favorite.")
                else:
                    await safe_send(ctx.channel, f"❌ {user.display_name} n’a pas encore de carte favorite.")
                return

            async with aiohttp.ClientSession() as session:
                for entry in cartes_data:
                    nom_carte = entry["cartefav"]
                    nom_encode = urllib.parse.quote(nom_carte)
                    carte = None

                    # Recherche API ygoprodeck (fr puis en)
                    for code in ["fr", ""]:
                        if code:
                            url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}&language={code}"
                        else:
                            url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"

                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if "data" in data and len(data["data"]) > 0:
                                    carte = data["data"][0]
                                    break

                    if not carte:
                        await safe_send(ctx.channel, f"❌ Carte favorite `{nom_carte}` introuvable via l’API.")
                        continue

                    embed = discord.Embed(
                        description=f"La carte favorite de **{user.display_name}** est :",
                        color=discord.Color.red()
                    )
                    embed.set_image(url=carte["card_images"][0]["image_url"])

                    await safe_send(ctx.channel, embed=embed)

        except Exception as e:
            print(f"[ERREUR cartefav] {e}")
            await safe_send(ctx.channel, "🚨 Une erreur est survenue lors de la récupération des cartes favorites.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CarteFav(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
