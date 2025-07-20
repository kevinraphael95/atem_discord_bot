# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif : Rechercher et afficher les détails d’une carte Yu-Gi-Oh! dans plusieurs langues avec un bouton pour ajouter en favoris
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import urllib.parse

from utils.discord_utils import safe_send  # ✅ Protection 429
from supabase_client import supabase       # Client Supabase déjà configuré

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton Ajouter Carte Favorite
# ────────────────────────────────────────────────────────────────────────────────
class CarteFavoriteButton(View):
    def __init__(self, carte_name: str, user: discord.User):
        super().__init__(timeout=120)
        self.carte_name = carte_name
        self.user = user

    @discord.ui.button(label="Carte favorite", style=discord.ButtonStyle.primary, emoji="⭐")
    async def add_favorite(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Ce bouton n’est pas pour toi.", ephemeral=True)
            return
        try:
            supabase.table("favorites").insert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "cartefav": self.carte_name
            }).execute()
            await interaction.response.send_message(f"✅ **{self.carte_name}** ajoutée à tes cartes favorites !", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR Supabase] {e}")
            await interaction.response.send_message("❌ Erreur lors de l’ajout à Supabase.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Carte(commands.Cog):
    """
    Commande !carte — Rechercher une carte Yu-Gi-Oh! et afficher ses informations.
    Affiche un bouton "⭐ Carte favorite" pour enregistrer la carte en favoris.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="carte",
        aliases=["card"],
        help="🔍 Rechercher une carte Yu-Gi-Oh! dans plusieurs langues.",
        description="Affiche les infos d’une carte Yu-Gi-Oh! à partir de son nom (FR, EN)."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def carte(self, ctx: commands.Context, *, nom: str):
        """Commande principale pour rechercher et afficher une carte Yu-Gi-Oh!"""
        lang_codes = ["fr", ""]  # fr puis en (vide = défaut)
        nom_encode = urllib.parse.quote(nom)
        carte = None
        langue_detectee = "?"
        nom_corrige = nom

        try:
            async with aiohttp.ClientSession() as session:
                for code in lang_codes:
                    if code:
                        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}&language={code}"
                    else:
                        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"

                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "data" in data and len(data["data"]) > 0:
                                carte = data["data"][0]
                                langue_detectee = code if code else "en"
                                nom_corrige = carte.get("name", nom)
                                break

                # Recherche floue si pas trouvé
                if not carte:
                    url_fuzzy = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}"
                    async with session.get(url_fuzzy) as resp_fuzzy:
                        if resp_fuzzy.status == 200:
                            data_fuzzy = await resp_fuzzy.json()
                            suggestions = data_fuzzy.get("data", [])
                            if suggestions:
                                noms = [c.get("name") for c in suggestions[:3]]
                                suggestion_msg = "\n".join(f"• **{n}**" for n in noms)
                                await safe_send(ctx.channel, f"❌ Carte introuvable pour `{nom}`.\n🔎 Suggestions :\n{suggestion_msg}")
                                return

        except Exception as e:
            print(f"[ERREUR carte] {e}")
            await safe_send(ctx.channel, "🚨 Une erreur est survenue lors de la recherche.")
            return

        if not carte:
            await safe_send(ctx.channel, f"❌ Carte introuvable. Vérifie l’orthographe exacte : `{nom}`.")
            return

        if nom_corrige.lower() != nom.lower():
            await safe_send(ctx.channel, f"🔍 Résultat trouvé pour **{nom_corrige}** ({langue_detectee.upper()})")

        embed = discord.Embed(
            title=f"{carte.get('name', 'Carte inconnue')} ({langue_detectee.upper()})",
            description=carte.get("desc", "Pas de description disponible."),
            color=discord.Color.red()
        )

        embed.add_field(name="🧪 Type", value=carte.get("type", "?"), inline=True)

        if carte.get("type", "").lower().startswith("monstre"):
            embed.add_field(name="⚔️ ATK / DEF", value=f"{carte.get('atk', '?')} / {carte.get('def', '?')}", inline=True)
            embed.add_field(name="⭐ Niveau / Rang", value=str(carte.get("level", "?")), inline=True)
            embed.add_field(name="🌪️ Attribut", value=carte.get("attribute", "?"), inline=True)
            embed.add_field(name="👹 Race", value=carte.get("race", "?"), inline=True)

        embed.set_thumbnail(url=carte["card_images"][0]["image_url"])

        view = CarteFavoriteButton(carte["name"], ctx.author)
        await safe_send(ctx.channel, embed=embed, view=view)

    def cog_load(self):
        self.carte.category = "🃏 Yu-Gi-Oh!"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Carte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
