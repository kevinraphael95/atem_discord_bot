# ────────────────────────────────────────────────────────────────
# 📌 ygoblackjack.py
# Objectif : Jouer au blackjack avec les cartes Yu-Gi-Oh! (valeur = ATK)
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
from utils.discord_utils import safe_send, safe_edit
from utils.card_utils import fetch_random_card
import aiohttp
import random

# ────────────────────────────────────────────────────────────────
# 🔹 Helper pour calculer la valeur de blackjack d’une carte
# ────────────────────────────────────────────────────────────────
def card_value(attack: int) -> int:
    """Convertit l'ATK d'une carte en valeur blackjack."""
    if attack is None or attack <= 0:
        return 1
    return attack // 100

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

        self.add_item(Button(label="Tirer 🃏", style=discord.ButtonStyle.green, custom_id="hit"))
        self.add_item(Button(label="Rester ✋", style=discord.ButtonStyle.red, custom_id="stand"))

    async def on_timeout(self):
        if not self.game_over:
            await self.end_game("⏰ Temps écoulé ! Partie terminée.")
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def end_game(self, msg):
        self.game_over = True
        player_total = sum(card_value(c["atk"]) for c in self.player_cards)
        dealer_total = sum(card_value(c["atk"]) for c in self.dealer_cards)

        result = ""
        if player_total > 21:
            result = "💀 Bust ! Tu as dépassé 21."
        elif dealer_total > 21 or player_total > dealer_total:
            result = "🏆 Tu gagnes !"
        elif player_total < dealer_total:
            result = "😢 Tu perds !"
        else:
            result = "⚖️ Égalité !"

        embed = discord.Embed(title="Résultat du Blackjack YGO", color=discord.Color.blue())
        embed.add_field(name="Tes cartes", value="\n".join(f"{c['name']} ({c['atk'] or 0} ATK)" for c in self.player_cards) + f"\n**Total : {player_total}**", inline=False)
        embed.add_field(name="Cartes du dealer", value="\n".join(f"{c['name']} ({c['atk'] or 0} ATK)" for c in self.dealer_cards) + f"\n**Total : {dealer_total}**", inline=False)
        embed.add_field(name="Résultat", value=result, inline=False)

        for child in self.children:
            child.disabled = True
        await safe_edit(self.message, embed=embed, view=self)

    @discord.ui.button(label="Tirer 🃏", style=discord.ButtonStyle.green, custom_id="hit")
    async def hit(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            return
        card, _ = await fetch_random_card(self.session)
        if card:
            self.player_cards.append(card)
            total = sum(card_value(c["atk"]) for c in self.player_cards)
            content = f"Tu as tiré : **{card['name']} ({card['atk'] or 0} ATK)**\nTotal actuel : **{total}**"
            if total > 21:
                await self.end_game("💀 Bust !")
            else:
                await safe_edit(interaction.message, content=content, view=self)

    @discord.ui.button(label="Rester ✋", style=discord.ButtonStyle.red, custom_id="stand")
    async def stand(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            return
        # Dealer tire jusqu’à 17+
        while sum(card_value(c["atk"]) for c in self.dealer_cards) < 17:
            card, _ = await fetch_random_card(self.session)
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

        # Tirage initial
        for _ in range(2):
            card, _ = await fetch_random_card(self.session)
            if card:
                player_cards.append(card)
        card, _ = await fetch_random_card(self.session)
        if card:
            dealer_cards.append(card)

        view = BlackjackView(self.bot, self.session, player_cards, dealer_cards)
        view.message = await safe_send(channel, "🃏 Blackjack YGO — Ta main :", view=view)

    def cog_unload(self):
        # Fermer la session aiohttp
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
