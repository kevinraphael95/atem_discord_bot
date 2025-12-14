# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator_yugioh.py — Akinator intelligent pour deviner une carte Yu-Gi-Oh!
# Catégorie : Fun
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorYuGiOh(commands.Cog):
    """
    Commande /akinator_yugioh et !akinator_yugioh — Devine la carte Yu-Gi-Oh! du joueur
    """
    API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
    MAX_CARDS = 50

    TYPES = ["Normal Monster", "Effect Monster", "Fusion Monster", "Synchro Monster",
             "XYZ Monster", "Link Monster", "Spell Card", "Trap Card"]
    RACES = ["Aqua", "Beast", "Beast-Warrior", "Creator-God", "Cyberse", "Dinosaur",
             "Divine-Beast", "Dragon", "Fairy", "Fiend", "Fish", "Insect", "Machine",
             "Plant", "Psychic", "Pyro", "Reptile", "Rock", "Sea Serpent", "Spellcaster",
             "Thunder", "Warrior", "Winged Beast", "Wyrm", "Zombie",
             "Normal", "Field", "Equip", "Continuous", "Quick-Play", "Ritual",
             "Counter"]
    ATTRIBUTES = ["DARK", "EARTH", "FIRE", "LIGHT", "WATER", "WIND", "DIVINE"]

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction utilitaire pour l'API (async)
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_cards(self, filters):
        params = filters.copy()
        params["num"] = self.MAX_CARDS
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, params=params) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data.get("data", [])
        except Exception:
            return []

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Pose une question oui/non au joueur
    # ────────────────────────────────────────────────────────────────────────────
    async def ask_question(self, ctx_or_inter, question):
        def check(m):
            return m.author.id == getattr(ctx_or_inter, "user", ctx_or_inter.author).id and \
                   m.content.lower() in ["oui", "non", "o", "n"]

        await safe_send(getattr(ctx_or_inter, "channel", ctx_or_inter.channel), f"{question} (oui/non)")
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            return msg.content.lower() in ["oui", "o"]
        except:
            await safe_send(getattr(ctx_or_inter, "channel", ctx_or_inter.channel), "⏰ Temps écoulé, arrêt du jeu.")
            return None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Boucle principale du jeu
    # ────────────────────────────────────────────────────────────────────────────
    async def akinator_game(self, ctx_or_inter):
        filters = {}
        cards = await self.fetch_cards(filters)
        if not cards:
            await safe_send(getattr(ctx_or_inter, "channel", ctx_or_inter.channel), "❌ Impossible de récupérer les cartes.")
            return

        while len(cards) > 1:
            if "type" not in filters:
                options = self.TYPES
                filter_name = "type"
            elif "race" not in filters and any("Monster" in c["type"] for c in cards):
                options = self.RACES
                filter_name = "race"
            elif "attribute" not in filters and any("Monster" in c["type"] for c in cards):
                options = self.ATTRIBUTES
                filter_name = "attribute"
            else:
                break

            answered = False
            for option in options:
                yes = await self.ask_question(ctx_or_inter, f"Est-ce que la carte est '{option}' ?")
                if yes is None:
                    return
                if yes:
                    filters[filter_name] = option
                    answered = True
                    break
            if not answered:
                break

            cards = await self.fetch_cards(filters)

        # Affichage résultat
        if not cards:
            await safe_send(getattr(ctx_or_inter, "channel", ctx_or_inter.channel), "Aucune carte trouvée 😢")
        elif len(cards) == 1:
            card = cards[0]
            msg = (
                f"🎴 La carte est probablement : **{card['name']}**\n"
                f"Type : {card['type']}, Race : {card.get('race','N/A')}, Attribut : {card.get('attribute','N/A')}\n"
                f"Description : {card['desc']}\n"
                f"Image : {card['card_images'][0]['image_url']}"
            )
            await safe_send(getattr(ctx_or_inter, "channel", ctx_or_inter.channel), msg)
        else:
            await safe_send(getattr(ctx_or_inter, "channel", ctx_or_inter.channel),
                            "Plusieurs cartes possibles :\n" + "\n".join([c["name"] for c in cards]))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="akinator_yugioh",
        description="Devine la carte Yu-Gi-Oh! à laquelle tu penses."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_akinator_yugioh(self, interaction: discord.Interaction):
        await safe_respond(interaction, "🎴 Démarrage de l'Akinator Yu-Gi-Oh! ...")
        await self.akinator_game(interaction)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="akinator_yugioh")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_akinator_yugioh(self, ctx: commands.Context):
        await safe_send(ctx.channel, "🎴 Démarrage de l'Akinator Yu-Gi-Oh! ...")
        await self.akinator_game(ctx)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorYuGiOh(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
