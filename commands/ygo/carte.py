# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif : Rechercher et afficher les détails d’une carte Yu-Gi-Oh! dans plusieurs langues
#           avec réaction emoji pour afficher les prix des raretés par set
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
import asyncio

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Carte(commands.Cog):
    """
    Commande !carte — Rechercher une carte Yu-Gi-Oh! et afficher ses informations.
    Permet via réaction 💶 d’afficher les prix des sets et raretés.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._message_carte_cache = {}  # {message.id: carte_data}

    @commands.command(
        name="carte",
        aliases=["card"],
        help="🔍 Rechercher une carte Yu-Gi-Oh! dans plusieurs langues.",
        description="Affiche les infos d’une carte Yu-Gi-Oh! à partir de son nom (FR, EN)."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def carte(self, ctx: commands.Context, *, nom: str):
        """Commande principale pour chercher une carte Yu-Gi-Oh!"""

        lang_codes = ["fr", ""]  # 🔧 FR, puis défaut (EN sans paramètre)
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
                            if "data" in data:
                                carte = data["data"][0]
                                langue_detectee = code if code else "en"
                                nom_corrige = carte.get("name", nom)
                                break
                        elif resp.status == 400:
                            continue
                        else:
                            await ctx.send("🚨 Erreur : Impossible de récupérer les données depuis l’API.")
                            return

                # Ajout : recherche approximative si carte non trouvée
                if not carte:
                    url_fuzzy = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}"
                    async with session.get(url_fuzzy) as resp_fuzzy:
                        if resp_fuzzy.status == 200:
                            data_fuzzy = await resp_fuzzy.json()
                            suggestions = data_fuzzy.get("data", [])
                            if suggestions:
                                noms_proches = [c.get("name") for c in suggestions[:3]]
                                msg_suggestions = "\n".join(f"• **{n}**" for n in noms_proches)
                                await ctx.send(
                                    f"❌ Carte introuvable pour `{nom}`.\n"
                                    f"🔎 Vouliez-vous dire :\n{msg_suggestions}"
                                )
                                return

        except Exception as e:
            print(f"[ERREUR commande !carte] {e}")
            await ctx.send("🚨 Erreur inattendue lors de la récupération des données.")
            return

        if not carte:
            await ctx.send(f"❌ Carte introuvable en français ou en anglais. Vérifie l’orthographe exacte : `{nom}`.")
            return

        if nom_corrige.lower() != nom.lower():
            await ctx.send(f"🔍 Résultat trouvé pour **{nom_corrige}** ({langue_detectee.upper()})")

        embed = discord.Embed(
            title=f"{carte.get('name', 'Carte inconnue')} ({langue_detectee.upper()})",
            description=carte.get("desc", "Pas de description disponible."),
            color=discord.Color.red()
        )

        embed.add_field(name="🧪 Type", value=carte.get("type", "?"), inline=True)

        if carte.get("type", "").lower().startswith("monstre"):
            atk = carte.get("atk", "?")
            defe = carte.get("def", "?")
            level = carte.get("level", "?")
            attr = carte.get("attribute", "?")
            race = carte.get("race", "?")

            embed.add_field(name="⚔️ ATK / DEF", value=f"{atk} / {defe}", inline=True)
            embed.add_field(name="⭐ Niveau / Rang", value=str(level), inline=True)
            embed.add_field(name="🌪️ Attribut", value=attr, inline=True)
            embed.add_field(name="👹 Race", value=race, inline=True)

        embed.set_thumbnail(url=carte["card_images"][0]["image_url"])
        message = await ctx.send(embed=embed)

        # Ajouter la réaction euro (💶)
        emoji = "💶"
        await message.add_reaction(emoji)

        # Stocker la carte liée au message
        self._message_carte_cache[message.id] = carte

        # Nettoyer le cache après 5 minutes
        async def cleanup_cache(msg_id):
            await asyncio.sleep(300)
            self._message_carte_cache.pop(msg_id, None)

        self.bot.loop.create_task(cleanup_cache(message.id))

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        # Ignore les réactions du bot
        if user.bot:
            return

        if reaction.emoji != "💶":
            return

        message = reaction.message

        if message.id not in self._message_carte_cache:
            return

        carte = self._message_carte_cache[message.id]

        # Retirer la réaction utilisateur pour éviter les spams
        try:
            await message.remove_reaction("💶", user)
        except discord.errors.Forbidden:
            pass  # Pas la permission, on ignore
        # 🔗 Lien direct vers Cardmarket dans la bonne langue
        langue_cm = "FR" if carte.get("lang", "en") == "fr" else "EN"
        nom_cm = urllib.parse.quote(carte["name"])
        url_cm = f"https://www.cardmarket.com/{langue_cm}/YuGiOh/Products/Search?searchString={nom_cm}"

        embed = discord.Embed(
            title=f"💶 Voir les offres Cardmarket pour {carte['name']}",
            description=f"[🔗 Cliquez ici pour voir sur Cardmarket]({url_cm})",
            color=discord.Color.gold()
        )

        await message.channel.send(embed=embed)


    def cog_load(self):
        self.carte.category = "🃏 Yu-Gi-Oh!"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Carte(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
