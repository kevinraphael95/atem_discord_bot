# ────────────────────────────────────────────────────────────────────────────────
# 📌 carte.py — Commande interactive !carte
# Objectif : Rechercher et afficher les détails d’une carte Yu-Gi-Oh! dans plusieurs langues
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import asyncio
import urllib.parse

from utils.discord_utils import safe_send, safe_edit  # ✅ Protection 429

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Carte(commands.Cog):
    """
    Commande !carte — Rechercher une carte Yu-Gi-Oh! et afficher ses informations.
    Réagit avec 💶 pour proposer un lien Cardmarket.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._message_carte_cache = {}

    @commands.command(
        name="carte",
        aliases=["card"],
        help="🔍 Rechercher une carte Yu-Gi-Oh! dans plusieurs langues.",
        description="Affiche les infos d’une carte Yu-Gi-Oh! à partir de son nom (FR, EN)."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def carte(self, ctx: commands.Context, *, nom: str):
        """Commande principale pour chercher une carte Yu-Gi-Oh!"""
        lang_codes = ["fr", ""]
        nom_encode = urllib.parse.quote(nom)
        carte = None
        langue_detectee, nom_corrige = "?", nom

        try:
            async with aiohttp.ClientSession() as session:
                for code in lang_codes:
                    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}&language={code}" if code else \
                          f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "data" in data:
                                carte = data["data"][0]
                                langue_detectee = code if code else "en"
                                nom_corrige = carte.get("name", nom)
                                break

                # 🔁 Suggestion si aucune carte trouvée
                if not carte:
                    url_fuzzy = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}"
                    async with session.get(url_fuzzy) as resp_fuzzy:
                        if resp_fuzzy.status == 200:
                            data_fuzzy = await resp_fuzzy.json()
                            suggestions = data_fuzzy.get("data", [])
                            if suggestions:
                                noms = [c.get("name") for c in suggestions[:3]]
                                suggestion_msg = "\n".join(f"• **{n}**" for n in noms)
                                return await safe_send(ctx.channel, f"❌ Carte introuvable pour `{nom}`.\n🔎 Suggestions :\n{suggestion_msg}")
        except Exception as e:
            print(f"[ERREUR carte] {e}")
            return await safe_send(ctx.channel, "🚨 Une erreur est survenue lors de la recherche.")

        if not carte:
            return await safe_send(ctx.channel, f"❌ Carte introuvable. Vérifie l’orthographe exacte : `{nom}`.")

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
        message = await safe_send(ctx.channel, embed=embed)

        await message.add_reaction("💶")
        self._message_carte_cache[message.id] = carte

        async def cleanup(msg_id):
            await asyncio.sleep(300)
            self._message_carte_cache.pop(msg_id, None)

        self.bot.loop.create_task(cleanup(message.id))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔁 Listener — Ajout de réaction 💶
    # ────────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or reaction.emoji != "💶":
            return

        message = reaction.message
        if message.id not in self._message_carte_cache:
            return

        carte = self._message_carte_cache[message.id]

        try:
            await message.remove_reaction("💶", user)
        except discord.Forbidden:
            pass

        nom_cm = urllib.parse.quote(carte["name"])
        langue_cm = "FR" if carte.get("lang", "en") == "fr" else "EN"
        url = f"https://www.cardmarket.com/{langue_cm}/YuGiOh/Products/Search?searchString={nom_cm}"

        embed = discord.Embed(
            title=f"💶 Voir les offres Cardmarket pour {carte['name']}",
            description=f"[🔗 Cliquez ici pour voir sur Cardmarket]({url})",
            color=discord.Color.gold()
        )

        await safe_send(message.channel, embed=embed)

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
