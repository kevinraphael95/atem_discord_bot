# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygoblackjack.py
# Objectif : Jouer au blackjack avec cartes Yu-Gi-Oh! (valeur = niveau)
# Catégorie : Fun
# Accès : Tous
# Cooldown : 10s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import random
import asyncio

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Helper pour calculer la valeur d'une carte
# ────────────────────────────────────────────────────────────────────────────────
def card_value(level: int) -> int:
    """La valeur d'une carte = son niveau."""
    if level is None or level < 1:
        return 1
    return level

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fetch batch de cartes monstres depuis YGOPRODeck
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_monster_batch(session: aiohttp.ClientSession, limit: int = 50, retries: int = 3):
    for attempt in range(retries):
        try:
            url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?type=Monster&language=fr"
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                cards = data.get("data", [])
                monsters = [c for c in cards if c.get("level") and c["level"] >= 1]
                if monsters:
                    random.shuffle(monsters)
                    return monsters[:limit]
        except Exception:
            await asyncio.sleep(1)
    return []

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Blackjack interactif
# ────────────────────────────────────────────────────────────────────────────────
class BlackjackView(View):
    def __init__(self, bot, session, player_cards, dealer_cards, card_pool):
        super().__init__(timeout=120)
        self.bot = bot
        self.session = session
        self.player_cards = player_cards
        self.dealer_cards = dealer_cards
        self.card_pool = card_pool
        self.message = None
        self.game_over = False

    async def draw_card(self):
        if not self.card_pool:
            self.card_pool = await fetch_monster_batch(self.session, 50)
            if not self.card_pool:
                return None
        return self.card_pool.pop()

    async def update_message(self, content=None):
        """Affiche la main actuelle dans un embed"""
        player_total = sum(card_value(c.get("level")) for c in self.player_cards)
        dealer_total = sum(card_value(c.get("level")) for c in self.dealer_cards)

        embed = discord.Embed(title="🃏 Blackjack YGO", color=discord.Color.blue())
        embed.add_field(
            name="Tes cartes",
            value="\n".join(f"{c['name']} - Niveau {c.get('level', 1)}" for c in self.player_cards) + f"\n**Total : {player_total}**",
            inline=False
        )
        # Cache la première carte du dealer
        if self.game_over:
            dealer_text = "\n".join(f"{c['name']} - Niveau {c.get('level',1)}" for c in self.dealer_cards) + f"\n**Total : {dealer_total}**"
        else:
            dealer_text = f"{self.dealer_cards[0]['name']} - Niveau {self.dealer_cards[0].get('level',1)}\n**Carte cachée**"
        embed.add_field(name="Cartes du dealer", value=dealer_text, inline=False)
        if content:
            embed.set_footer(text=content)
        await self.message.edit(embed=embed, view=self)

    async def end_game(self, msg):
        self.game_over = True
        for child in self.children:
            child.disabled = True
        await self.update_message(content=msg)

    # ── Bouton Tirer 🃏 ──
    @discord.ui.button(label="Tirer 🃏", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            return
        card = await self.draw_card()
        if not card:
            await interaction.response.send_message("❌ Impossible de récupérer les cartes.", ephemeral=True)
            return
        self.player_cards.append(card)
        total = sum(card_value(c.get("level")) for c in self.player_cards)
        if total > 21:
            await self.end_game("💀 Bust ! Tu as dépassé 21.")
        else:
            await self.update_message(content=f"Tu as tiré : {card['name']} - Niveau {card.get('level',1)}")
            await interaction.response.defer()

    # ── Bouton Rester ✋ ──
    @discord.ui.button(label="Rester ✋", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            return
        # Dealer tire jusqu'à 17+
        while sum(card_value(c.get("level")) for c in self.dealer_cards) < 17:
            card = await self.draw_card()
            if card:
                self.dealer_cards.append(card)
        # Calcul du résultat
        player_total = sum(card_value(c.get("level")) for c in self.player_cards)
        dealer_total = sum(card_value(c.get("level")) for c in self.dealer_cards)
        if dealer_total > 21 or player_total > dealer_total:
            result = "🏆 Tu gagnes !"
        elif player_total < dealer_total:
            result = "😢 Tu perds !"
        else:
            result = "⚖️ Égalité !"
        await self.end_game(f"🛑 Partie terminée : {result}")

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class YGOBlackjack(commands.Cog):
    """Blackjack avec cartes Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.card_pool = []

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Lancer une partie
    # ────────────────────────────────────────────────────────────────────────────
    async def start_game(self, channel):
        player_cards = []
        dealer_cards = []

        # Charger un lot de cartes
        if not self.card_pool:
            self.card_pool = await fetch_monster_batch(self.session, 50)
            if not self.card_pool:
                await channel.send("❌ Impossible de récupérer les cartes.")
                return

        # Tirage initial
        for _ in range(2):
            player_cards.append(self.card_pool.pop())
        dealer_cards.append(self.card_pool.pop())

        view = BlackjackView(self.bot, self.session, player_cards, dealer_cards, self.card_pool)
        view.message = await channel.send("🃏 Blackjack YGO — Ta main :")
        await view.update_message(content="Partie commencée !")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygoblackjack",
        description="Joue au blackjack avec cartes Yu-Gi-Oh! (niveau = valeur)."
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_ygoblackjack(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.start_game(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygoblackjack")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_ygoblackjack(self, ctx: commands.Context):
        await self.start_game(ctx.channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fermer la session aiohttp au déchargement du cog
    # ────────────────────────────────────────────────────────────────────────────
    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOBlackjack(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
