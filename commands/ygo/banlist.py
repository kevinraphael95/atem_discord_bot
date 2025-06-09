# ────────────────────────────────────────────────────────────────────────────────
# 📁 banlist.py — Commande !banlist
# ────────────────────────────────────────────────────────────────────────────────
# Ce module permet de récupérer et afficher la banlist TCG actuelle
# depuis l’API YGOPRODeck : cartes bannies, limitées, semi-limités.
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 IMPORTS
# ────────────────────────────────────────────────────────────────────────────────
import discord                            # 📦 API Discord
from discord.ext import commands          # 🧩 Gestion des commandes
import aiohttp                            # 🌐 Requêtes HTTP asynchrones

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 COG : BanlistCommand
# ────────────────────────────────────────────────────────────────────────────────
class BanlistCommand(commands.Cog):
    """
    📋 Commande permettant d’afficher la banlist TCG actuelle de Yu-Gi-Oh!.
    Données récupérées dynamiquement depuis l’API YGOPRODeck.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot  # 🔌 Stocke l'instance du bot pour usage dans les événements

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 COMMANDE : !banlist / !banned / !tcgban
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="banlist",
        aliases=["banned", "tcgban"],
        help="🔒 Affiche la banlist TCG actuelle (bannie, limitée, semi-limitée)."
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)  # 🧊 Anti-spam utilisateur
    async def banlist(self, ctx: commands.Context):
        """
        🔍 Récupère les cartes bannies, limitées et semi-limitées via API
        et affiche le tout dans un embed Discord.
        """

        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?banlist=tcg"  # 🌐 URL API

        try:
            # 🌍 Requête asynchrone vers l’API
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await ctx.send("🚨 Impossible de récupérer la banlist.")
                        return
                    data = await resp.json()

            # 📦 Initialisation des catégories
            banned = []        # ❌ Cartes interdites
            limited = []       # ⚠️ Cartes limitées (1 copie max)
            semi_limited = []  # ⚖️ Cartes semi-limités (2 copies max)

            # 🔍 Analyse des cartes reçues
            for card in data.get("data", []):
                name = card.get("name", "Carte inconnue")
                ban_status = card.get("banlist_info", {}).get("ban_tcg", None)

                # 📤 Tri selon le statut
                if ban_status == "Banned":
                    banned.append(name)
                elif ban_status == "Limited":
                    limited.append(name)
                elif ban_status == "Semi-Limited":
                    semi_limited.append(name)

            # 🧾 Fonction d'affichage formaté (avec coupe au-delà de 20 cartes)
            def format_cards(cards):
                return "\n".join(f"• {card}" for card in cards[:20]) + \
                    ("\n... *(liste coupée)*" if len(cards) > 20 else "")

            # 🎨 Création de l'embed final
            embed = discord.Embed(
                title="🚫 Banlist TCG — Yu-Gi-Oh!",
                description="🔄 Mise à jour dynamique via l’API YGOPRODeck",
                color=discord.Color.red()
            )
            embed.add_field(name="❌ Banni", value=format_cards(banned) or "Aucune carte", inline=False)
            embed.add_field(name="⚠️ Limité", value=format_cards(limited) or "Aucune carte", inline=False)
            embed.add_field(name="⚖️ Semi-limité", value=format_cards(semi_limited) or "Aucune carte", inline=False)
            embed.set_footer(text="📥 Source : https://db.ygoprodeck.com/api-guide/")

            await ctx.send(embed=embed)  # 📤 Envoi dans Discord

        except Exception as e:
            # ❌ Gestion des erreurs réseau ou parsing
            print(f"[ERREUR BANLIST] {e}")
            await ctx.send("💥 Une erreur est survenue lors de la récupération de la banlist.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🏷️ CATEGORISATION personnalisée pour !help
    # ────────────────────────────────────────────────────────────────────────────
    def cog_load(self):
        self.banlist.category = "🃏 Yu-Gi-Oh!"

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ SETUP DU COG
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    """
    🔁 Fonction appelée lors du chargement du cog.
    Elle ajoute le cog au bot et affiche une confirmation.
    """
    await bot.add_cog(BanlistCommand(bot))
    print("✅ Cog chargé : BanlistCommand (catégorie = 🃏 Yu-Gi-Oh!)")
