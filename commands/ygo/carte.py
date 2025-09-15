# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif : Rechercher et afficher les détails d’une carte Yu-Gi-Oh! avec embed ultra-optimisé
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
from utils.discord_utils import safe_send
from utils.supabase_client import supabase

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
            supabase.table("profil").delete().eq("user_id", str(interaction.user.id)).execute()
            supabase.table("profil").insert({
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
    Embed ultra-optimisé avec couleur dynamique fiable et boutons interactifs.
    """

    TYPE_COLOR = {
        "monster": discord.Color.red(),
        "spell": discord.Color.green(),
        "trap": discord.Color.blue()
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="carte",
        aliases=["card"],
        help="🔍 Rechercher une carte Yu-Gi-Oh! avec embed ultra-optimisé.",
        description="Affiche les infos d’une carte Yu-Gi-Oh! à partir de son nom (FR, EN)."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def carte(self, ctx: commands.Context, *, nom: str):
        nom_encode = urllib.parse.quote(nom)
        carte = None
        langue_detectee = "?"
        nom_corrige = nom

        # ───────────── Recherche carte
        try:
            async with aiohttp.ClientSession() as session:
                for code in ["fr", ""]:
                    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
                    if code:
                        url += f"&language={code}"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "data" in data and len(data["data"]) > 0:
                                carte = data["data"][0]
                                langue_detectee = code if code else "en"
                                nom_corrige = carte.get("name", nom)
                                break

                # ───────── Fuzzy search si pas trouvé
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

        # ───────── Type fiable pour couleur
        raw_type = carte.get("type", "").lower()
        color = discord.Color.dark_grey()
        if "monster" in raw_type:
            color = self.TYPE_COLOR["monster"]
        elif "spell" in raw_type:
            color = self.TYPE_COLOR["spell"]
        elif "trap" in raw_type:
            color = self.TYPE_COLOR["trap"]

        # ───────── Construction embed
        embed = discord.Embed(
            title=f"**{carte.get('name', 'Carte inconnue')}**",
            description=f"**Type** : {carte.get('type', '?')}\n**Race / Attribut** : {carte.get('race', '?')} / {carte.get('attribute', '?')}",
            color=color
        )

        if "monster" in raw_type:
            embed.add_field(
                name="Stats",
                value=f"Niveau/Rang : {carte.get('level', '?')}\nATK / DEF : {carte.get('atk', '?')} / {carte.get('def', '?')}",
                inline=False
            )

        embed.add_field(
            name="Description",
            value=carte.get('desc', 'Pas de description disponible.'),
            inline=False
        )

        # ───────── Thumbnail et image principale
        if "card_images" in carte and carte["card_images"]:
            embed.set_thumbnail(url=carte["card_images"][0].get("image_url_small", carte["card_images"][0]["image_url"]))
            embed.set_image(url=carte["card_images"][0]["image_url"])

        # ───────── Footer complet
        embed.set_footer(text=f"ID : {carte.get('id', '?')} | Langue : {langue_detectee.upper()}")

        # ───────── Bouton favori
        view = CarteFavoriteButton(carte["name"], ctx.author)
        await safe_send(ctx.channel, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Carte(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
