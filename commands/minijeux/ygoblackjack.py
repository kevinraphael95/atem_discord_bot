# ────────────────────────────────────────────────────────────────
# 📌 ygoblackjack.py
# Objectif : Jouer au blackjack avec les cartes Yu-Gi-Oh! (valeur = niveau)
# Catégorie : Fun
# Accès : Tous
# Cooldown : 10s
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import random

# ────────────────────────────────────────────────────────────────
# 🔹 Helper pour calculer la valeur de blackjack d’une carte
# ────────────────────────────────────────────────────────────────
def card_value(level: int) -> int:
    """Convertit le niveau d'une carte en valeur blackjack."""
    if level is None or level <= 0:
        return 1
    return level

# ────────────────────────────────────────────────────────────────
# 🔧 Fetch carte monstre aléatoire via YGOPRODeck
# ────────────────────────────────────────────────────────────────
async def fetch_random_monster(session: aiohttp.ClientSession):
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?type=Monster&language=fr"
    async with session.get(url) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()
        cards = data.get("data", [])
        if not cards:
            return None
        return random.choice(cards)

# ────────────────────────────────────────────────────────────────
# 🎛️ UI — Blackjack interactif
# ────────────────────────────────────────────────────────────────
class BlackjackView(View):
    def __init__(self, bot, session, player_cards, dealer_cards):
        super().__init__(timeout=120)
        self.bot = bot
        self.session = session
        self.player_cards = player_cards
        self.dealer_cards = dealer_cards
        self.message = None
        self.game_over = False

    async def update_message(self, content=None):
        """Affiche la main actuelle dans un embed"""
        player_total = sum(card_value(c.get("level")) for c in self.player_cards)
        dealer_total = sum(card_value(c.get("level")) for c in self.dealer_cards)

        embed = discord.Embed(title="Blackjack YGO", color=discord.Color.blue())
        embed.add_field(
            name="Tes cartes",
            value="\n".join(f"{c['name']} - Niveau {c.get('level', 1)}" for c in self.player_cards) + f"\n**Total : {player_total}**",
            inline=False
        )
        embed.add_field(
            name="Cartes du dealer",
            value="\n".join(f"{c['name']} - Niveau {c.get('level', 1)}" for c in self.dealer_cards) + f"\n**Total : {dealer_total}**",
            inline=False
        )
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
        card = await fetch_random_monster(self.session)
        if not card:
            await interaction.response.send_message("❌ Impossible de récupérer une carte.", ephemeral=True)
            return
        self.player_cards.append(card)
        total = sum(card_value(c.get("level")) for c in self.player_cards)
        if total > 21:
            await self.end_game("💀 Bust ! Tu as dépassé 21.")
        else:
            await self.update_message(content=f"Tu as tiré : {card['name']} - Niveau {card.get('level', 1)}")
            await interaction.response.defer()  # Ne pas envoyer de message supplémentaire

    # ── Bouton Rester ✋ ──
    @discord.ui.button(label="Rester ✋", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            return
        # Dealer tire jusqu'à 17+
        while sum(card_value(c.get("level")) for c in self.dealer_cards) < 17:
            card = await fetch_random_monster(self.session)
            if card:
                self.dealer_cards.append(card)
        await self.end_game("🛑 Tu as choisi de rester.")

# ────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────
class YGOBlackjack(commands.Cog):
    """Blackjack avec cartes Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    @commands.command(name="ygoblackjack")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def prefix_ygoblackjack(self, ctx: commands.Context):
        await self.start_game(ctx.channel)

    async def start_game(self, channel):
        player_cards = []
        dealer_cards = []

        # ── Tirage initial
        for _ in range(2):
            card = await fetch_random_monster(self.session)
            if card:
                player_cards.append(card)
        card = await fetch_random_monster(self.session)
        if card:
            dealer_cards.append(card)

        view = BlackjackView(self.bot, self.session, player_cards, dealer_cards)
        # ── Envoi du message initial avec la main complète
        view.message = await channel.send("🃏 Blackjack YGO — Ta main :")
        await view.update_message(content="Partie commencée !")
        await view.message.edit(view=view)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

# ────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOBlackjack(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
