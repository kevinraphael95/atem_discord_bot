# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte ultra complète
# Objectif : Recherche Yu-Gi-Oh! avec embed complet (limites, rareté, liens, password)
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
            supabase.table("favorites").delete().eq("user_id", str(interaction.user.id)).execute()
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
    Commande !carte — Embed complet avec toutes les infos TCG, OCG, Master Duel, rareté et liens officiels.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.lang_codes = ["fr", "de", "it", "pt"]  # EN par défaut

    @commands.command(
        name="carte",
        aliases=["card"],
        help="🔍 Rechercher une carte Yu-Gi-Oh! avec embed complet",
        description="Affiche toutes les infos d’une carte Yu-Gi-Oh! (FR, EN, DE, IT, PT)"
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def carte(self, ctx: commands.Context, *, nom: str):
        nom_encode = urllib.parse.quote(nom)
        carte = None
        langue_detectee = "?"
        nom_corrige = nom

        # 🔹 Couleur selon type
        def color_for_card(card_type: str) -> discord.Color:
            t = card_type.lower()
            if "monster" in t or "monstre" in t:
                return discord.Color.red()
            elif "spell" in t or "magie" in t:
                return discord.Color.blue()
            elif "trap" in t or "piège" in t:
                return discord.Color.green()
            return discord.Color.dark_gray()

        try:
            async with aiohttp.ClientSession() as session:
                # 🔹 Recherche stricte
                for code in self.lang_codes + ["en"]:
                    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
                    if code != "en":
                        url += f"&language={code}"
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                        if "data" in data and len(data["data"]) > 0:
                            carte = data["data"][0]
                            langue_detectee = code
                            nom_corrige = carte.get("name", nom)
                            break

                # 🔹 Recherche floue
                if not carte:
                    for code in self.lang_codes + ["en"]:
                        url_fuzzy = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}"
                        if code != "en":
                            url_fuzzy += f"&language={code}"
                        async with session.get(url_fuzzy) as resp_fuzzy:
                            if resp_fuzzy.status != 200:
                                continue
                            data_fuzzy = await resp_fuzzy.json()
                            suggestions = data_fuzzy.get("data", [])
                            if suggestions:
                                noms = [c.get("name") for c in suggestions[:3]]
                                suggestion_msg = "\n".join(f"• **{n}**" for n in noms)
                                await safe_send(ctx.channel, f"❌ Carte introuvable pour `{nom}`.\n🔎 Voulez-vous dire :\n{suggestion_msg}")
                                return

        except Exception as e:
            print(f"[ERREUR carte] {e}")
            await safe_send(ctx.channel, "🚨 Une erreur est survenue lors de la recherche.")
            return

        if not carte:
            await safe_send(ctx.channel, f"❌ Carte introuvable : `{nom}`.")
            return

        if nom_corrige.lower() != nom.lower():
            await safe_send(ctx.channel, f"🔍 Résultat trouvé pour **{nom_corrige}** ({langue_detectee.upper()})")

        # 🔹 Embed complet
        embed = discord.Embed(
            title=f"{carte.get('name', 'Carte inconnue')} ({langue_detectee.upper()})",
            description=carte.get("desc", "Pas de description disponible."),
            color=color_for_card(carte.get("type", ""))
        )

        # Type en français
        type_fr = carte.get("type", "?")
        if langue_detectee != "fr":
            type_fr = carte.get("type")  # simplification : utiliser le type tel quel
        embed.add_field(name="🧪 Type", value=type_fr, inline=True)

        # Monstres
        if "monstre" in carte.get("type", "").lower() or "monster" in carte.get("type", "").lower():
            embed.add_field(name="⚔️ ATK / DEF", value=f"{carte.get('atk', '?')} / {carte.get('def', '?')}", inline=True)
            embed.add_field(name="⭐ Niveau / Rang", value=str(carte.get("level", "?")), inline=True)
            embed.add_field(name="🌪️ Attribut", value=carte.get("attribute", "?"), inline=True)
            embed.add_field(name="👹 Race", value=carte.get("race", "?"), inline=True)

        # Limites et rareté
        limits = carte.get("banlist_info", {})
        embed.add_field(name="📜 Limite TCG", value=limits.get("tcg", "—"), inline=True)
        embed.add_field(name="📜 Limite OCG", value=limits.get("ocg", "—"), inline=True)
        embed.add_field(name="📜 Limite Master Duel", value=limits.get("masterduel", "—"), inline=True)
        embed.add_field(name="💎 Rareté Master Duel", value=limits.get("md_rare", "—"), inline=True)

        # Password
        embed.add_field(name="🔑 Password", value=carte.get("id", "?"), inline=True)

        # Liens officiels
        links = [
            f"[YGO DB](https://www.db.yugioh-card.com/yugiohdb/card_search.action?ope=2&cid={carte.get('id','')})",
            f"[OCG Ruling](https://www.db.yugioh-card.com/yugiohdb/card_list.action?ope=2&cid={carte.get('id','')})",
            f"[YugiPedia](https://yugipedia.com/wiki/{urllib.parse.quote(carte.get('name',''))})",
            f"[YGOPRODeck](https://ygoprodeck.com/card/?search={urllib.parse.quote(carte.get('name',''))})"
        ]
        embed.add_field(name="🔗 Liens utiles", value="\n".join(links), inline=False)

        # Image plus petite
        if "card_images" in carte and carte["card_images"]:
            embed.set_image(url=carte["card_images"][0]["image_url"])
            embed.set_thumbnail(url=carte["card_images"][0]["image_url"])  # miniature

        embed.set_footer(text=f"ID Carte : {carte.get('id', '?')}")

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
