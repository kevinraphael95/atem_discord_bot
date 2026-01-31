# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygoblackjack.py
# Objectif : Jouer au blackjack avec cartes Yu-Gi-Oh! (valeur = niveau des monstres)
# Catégorie : Fun
# Accès : Tous
# Cooldown : 10s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import random
import asyncio

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Helper pour calculer la valeur blackjack d’une carte
# ────────────────────────────────────────────────────────────────────────────────
def card_value(level: int) -> int:
    """Retourne la valeur blackjack d'une carte (niveau)."""
    if level is None or level < 1:
        return 1
    return level

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fetch 50 cartes monstres de niveau 1+ via YGOPRODeck
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_monsters(session: aiohttp.ClientSession):
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?type=Monster&language=fr"
    async with session.get(url) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()
        cards = data.get("data", [])
        # Filtrer que les monstres de niveau 1 ou plus
        monsters = [c for c in cards if c.get("level", 0) >= 1]
        random.shuffle(monsters)
        return monsters[:50]

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Blackjack interactif
# ────────────────────────────────────────────────────────────────────────────────
class BlackjackView(View):
    def __init__(self, bot, session, player_cards, dealer_cards, deck):
        super().__init__(timeout=120)
        self.bot = bot
        self.session = session
        self.player_cards = player_cards
        self.dealer_cards = dealer_cards
        self.deck = deck
        self.message = None
        self.game_over = False

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
        # Afficher seulement la première carte du dealer (comme Blackjack classique)
        dealer_display = f"{self.dealer_cards[0]['name']} - Niveau {self.dealer_cards[0].get('level',1)}\n**Carte cachée**"
        embed.add_field(
            name="Cartes du dealer",
            value=dealer_display,
            inline=False
        )
        if content:
            embed.set_footer(text=content)
        await self.message.edit(embed=embed, view=self)

    async def end_game(self, msg):
        self.game_over = True
        for child in self.children:
            child.disabled = True

        player_total = sum(card_value(c.get("level")) for c in self.player_cards)
        dealer_total = sum(card_value(c.get("level")) for c in self.dealer_cards)

        embed = discord.Embed(title="🃏 Blackjack YGO — Résultat", color=discord.Color.green())
        embed.add_field(
            name="Tes cartes",
            value="\n".join(f"{c['name']} - Niveau {c.get('level',1)}" for c in self.player_cards) + f"\n**Total : {player_total}**",
            inline=False
        )
        embed.add_field(
            name="Cartes du dealer",
            value="\n".join(f"{c['name']} - Niveau {c.get('level',1)}" for c in self.dealer_cards) + f"\n**Total : {dealer_total}**",
            inline=False
        )
        embed.add_field(name="Résultat", value=msg, inline=False)
        await self.message.edit(embed=embed, view=self)

    # ── Bouton Tirer 🃏 ──
    @discord.ui.button(label="Tirer 🃏", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            return
        if not self.deck:
            # Recharger 50 cartes si le deck est vide
            self.deck = await fetch_monsters(self.session)
            if not self.deck:
                await interaction.response.send_message("❌ Impossible de récupérer les cartes.", ephemeral=True)
                return
        card = self.deck.pop()
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
            if not self.deck:
                self.deck = await fetch_monsters(self.session)
                if not self.deck:
                    break
            card = self.deck.pop()
            self.dealer_cards.append(card)
        # Déterminer résultat
        player_total = sum(card_value(c.get("level")) for c in self.player_cards)
        dealer_total = sum(card_value(c.get("level")) for c in self.dealer_cards)
        if dealer_total > 21 or player_total > dealer_total:
            msg = "🏆 Tu gagnes !"
        elif player_total < dealer_total:
            msg = "😢 Tu perds !"
        else:
            msg = "⚖️ Égalité !"
        await self.end_game(msg)
        await interaction.response.defer()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class YGOBlackjack(commands.Cog):
    """Blackjack avec cartes Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def start_game(self, channel):
        deck = await fetch_monsters(self.session)
        if not deck:
            await safe_send(channel, "❌ Impossible de récupérer les cartes.")
            return

        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop()]

        view = BlackjackView(self.bot, self.session, player_cards, dealer_cards, deck)
        view.message = await channel.send("🃏 Blackjack YGO — Ta main :")
        await view.update_message(content="Partie commencée !")

    # ── Commande SLASH
    @app_commands.command(
        name="ygoblackjack",
        description="Jouer au Blackjack avec des cartes Yu-Gi-Oh!"
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_ygoblackjack(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.start_game(interaction.channel)
        await interaction.delete_original_response()

    # ── Commande PREFIX
    @commands.command(name="ygoblackjack")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def prefix_ygoblackjack(self, ctx: commands.Context):
        await self.start_game(ctx.channel)

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
