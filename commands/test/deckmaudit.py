# ────────────────────────────────────────────────────────────────────────────────
# 📌 deckmaudit.py — Commande absurde !deckwtf
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands
from discord.ui import View, Button
import random
import aiohttp
import asyncio
import logging

# Active le log DEBUG global
logging.basicConfig(level=logging.DEBUG)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton pour régénérer un deck
# ────────────────────────────────────────────────────────────────────────────────

class RegenerateDeckView(View):
    def __init__(self, bot, author: discord.User):
        super().__init__(timeout=60)
        self.bot = bot
        self.author = author
        self.add_item(RegenerateButton(bot, self))

class RegenerateButton(Button):
    def __init__(self, bot, parent_view):
        super().__init__(label="🔁 Régénérer le deck", style=discord.ButtonStyle.danger)
        self.bot = bot
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.author:
            await interaction.response.send_message("❌ Tu ne peux pas régénérer ce deck.", ephemeral=True)
            return

        await interaction.response.defer()
        embed = await generate_maudit_deck()
        await interaction.edit_original_response(embed=embed, view=self.parent_view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔮 Génération du deck maudit
# ────────────────────────────────────────────────────────────────────────────────

async def generate_maudit_deck():
    try:
        print("[DEBUG] Fonction generate_maudit_deck appelée")

        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        print(f"[DEBUG] Tentative de connexion à l’API : {url}")

        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                print(f"[DEBUG] Réponse reçue : {response.status}")
                if response.status != 200:
                    return discord.Embed(
                        title="❌ Erreur API",
                        description="L'API YGOPRODeck ne répond pas correctement.",
                        color=discord.Color.red()
                    )
                json_data = await response.json()
                all_cards = json_data.get("data", [])
                print(f"[DEBUG] Nombre total de cartes reçues : {len(all_cards)}")

        keywords = ["dice", "coin", "random", "gamble", "guess", "flip"]

        cards_with_keywords = []
        fallback_cards = []

        for card in all_cards:
            if "desc" not in card or not isinstance(card["desc"], str):
                continue
            if card.get("banlist_info"):
                continue

            desc = card["desc"].lower()
            num_sets = len(card.get("card_sets", []))
            prices = card.get("card_prices", [])
            low_price = 10_000_000
            if prices:
                try:
                    price_str = prices[0].get("tcgplayer_price")
                    if price_str:
                        low_price = float(price_str)
                except Exception as e:
                    print(f"[WARNING] Erreur prix : {e}")

            if any(kw in desc for kw in keywords) and num_sets <= 3:
                cards_with_keywords.append((card, num_sets, low_price))
            else:
                fallback_cards.append((card, num_sets, low_price))

        cards_with_keywords.sort(key=lambda x: (x[1], x[2]))
        fallback_cards.sort(key=lambda x: (x[1], x[2]))

        chosen_cards = [card[0] for card in cards_with_keywords[:40]]

        if len(chosen_cards) < 40:
            for card in fallback_cards:
                if card[0] not in chosen_cards:
                    chosen_cards.append(card[0])
                    if len(chosen_cards) >= 40:
                        break

        if len(chosen_cards) < 40:
            return discord.Embed(
                title="💀 Deck Maudit",
                description="Pas assez de cartes absurdes ou appropriées trouvées (min 40).",
                color=discord.Color.red()
            )

        random.shuffle(chosen_cards)

        monsters, spells, traps = [], [], []

        for card in chosen_cards:
            name = card["name"]
            image_url = card["card_images"][0]["image_url"]
            card_type = card["type"]

            line = f"• {name} — [🔗 Voir la carte]({image_url})"
            if "Monster" in card_type:
                monsters.append(line)
            elif "Spell" in card_type:
                spells.append(line)
            elif "Trap" in card_type:
                traps.append(line)

        if not monsters and not spells and not traps:
            return discord.Embed(
                title="❌ Erreur",
                description="Aucune carte affichable n’a été trouvée.",
                color=discord.Color.red()
            )

        embed = discord.Embed(
            title="🃏 Deck Maudit Aléatoire",
            description="Voici 40 cartes totalement injouables, classées par type :",
            color=discord.Color.dark_purple()
        )
        

        def add_fields_safely(embed, title, lines):
            chunk = []
            total = 0
            for line in lines:
                if total + len(line) + 1 > 1024:
                    embed.add_field(name=title, value="\n".join(chunk), inline=False)
                    chunk = []
                    total = 0
                chunk.append(line)
                total += len(line) + 1
            if chunk:
                embed.add_field(name=title, value="\n".join(chunk), inline=False)

        # Ajout sécurisé des champs
        if monsters:
            add_fields_safely(embed, "👹 Monstres", monsters)
        if spells:
            add_fields_safely(embed, "✨ Magies", spells)
        if traps:
            add_fields_safely(embed, "💥 Pièges", traps)

        

        print("[DEBUG] Embed généré avec succès")
        return embed

    except Exception as e:
        print(f"[ERREUR FATALE] {e}")
        return discord.Embed(
            title="❌ Exception",
            description=f"Une erreur est survenue : {e}",
            color=discord.Color.red()
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class DeckMaudit(commands.Cog):
    """
    Commande !deckwtf — Génère un deck absurde avec des cartes inutiles
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="deckwtf",
        help="Génère un deck absurde à partir de cartes ridicules.",
        description="Deck injouable composé de cartes anciennes, peu éditées et absurdes."
    )
    async def deckmaudit(self, ctx: commands.Context):
        print("[DEBUG] Commande !deckwtf appelée")
        await ctx.send("🔮 Création d’un deck maudit en cours...")

        embed = await generate_maudit_deck()
        view = RegenerateDeckView(self.bot, ctx.author)

        await ctx.send(embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot):
    cog = DeckMaudit(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
