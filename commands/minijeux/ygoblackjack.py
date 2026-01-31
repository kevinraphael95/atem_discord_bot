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

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Helper pour calculer la valeur blackjack d’une carte
# ────────────────────────────────────────────────────────────────────────────────
def card_value(level: int) -> int:
    """Retourne la valeur blackjack d'une carte (niveau)."""
    return level if level and level > 0 else 1

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fetch 50 cartes monstres de niveau 1+ via YGOPRODeck
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_monsters(session: aiohttp.ClientSession):
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?type=Monster&language=fr"
    async with session.get(url) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()
        monsters = [c for c in data.get("data", []) if c.get("level", 0) >= 1]
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

    async def update_message(self, footer: str | None = None):
        """Met à jour l'embed de la partie en cours."""
        player_total = sum(card_value(c["level"]) for c in self.player_cards)

        embed = discord.Embed(
            title="🃏 Blackjack YGO",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Tes cartes :",
            value=(
                "\n".join(f"{c['name']} - Niveau {c['level']}" for c in self.player_cards)
                + f"\n**Total : {player_total}**"
            ),
            inline=False
        )

        embed.add_field(
            name="Cartes du dealer :",
            value=(
                f"{self.dealer_cards[0]['name']} - Niveau {self.dealer_cards[0]['level']}\n"
                "🂠 Carte cachée"
            ),
            inline=False
        )

        if footer:
            embed.set_footer(text=footer)

        await safe_edit(self.message, embed=embed, view=self)

    async def end_game(self, result: str):
        """Fin de partie et révélation du dealer."""
        self.game_over = True
        for child in self.children:
            child.disabled = True

        player_total = sum(card_value(c["level"]) for c in self.player_cards)
        dealer_total = sum(card_value(c["level"]) for c in self.dealer_cards)

        embed = discord.Embed(
            title="🃏 Blackjack YGO — Résultat",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Tes cartes :",
            value=(
                "\n".join(f"{c['name']} - Niveau {c['level']}" for c in self.player_cards)
                + f"\n**Total : {player_total}**"
            ),
            inline=False
        )

        embed.add_field(
            name="Cartes du dealer :",
            value=(
                "\n".join(f"{c['name']} - Niveau {c['level']}" for c in self.dealer_cards)
                + f"\n**Total : {dealer_total}**"
            ),
            inline=False
        )

        embed.add_field(name="Résultat", value=result, inline=False)

        await safe_edit(self.message, embed=embed, view=self)

    # ────────────────────────────────────────────────────────────────────────────
    # 🃏 Bouton — Tirer
    # ────────────────────────────────────────────────────────────────────────────
    @discord.ui.button(label="Tirer 🃏", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            return

        if not self.deck:
            self.deck = await fetch_monsters(self.session)

        card = self.deck.pop()
        self.player_cards.append(card)

        total = sum(card_value(c["level"]) for c in self.player_cards)
        if total > 21:
            await self.end_game("💀 Bust ! Tu as dépassé 21.")
        else:
            await self.update_message(
                footer=f"Tu as tiré : {card['name']} (Niveau {card['level']})"
            )

        await interaction.response.defer()

    # ────────────────────────────────────────────────────────────────────────────
    # ✋ Bouton — Rester
    # ────────────────────────────────────────────────────────────────────────────
    @discord.ui.button(label="Rester ✋", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            return

        while sum(card_value(c["level"]) for c in self.dealer_cards) < 17:
            if not self.deck:
                self.deck = await fetch_monsters(self.session)
            self.dealer_cards.append(self.deck.pop())

        player_total = sum(card_value(c["level"]) for c in self.player_cards)
        dealer_total = sum(card_value(c["level"]) for c in self.dealer_cards)

        if dealer_total > 21 or player_total > dealer_total:
            result = "🏆 Tu gagnes !"
        elif player_total < dealer_total:
            result = "😢 Tu perds !"
        else:
            result = "⚖️ Égalité !"

        await self.end_game(result)
        await interaction.response.defer()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class YGOBlackjack(commands.Cog):
    """Commande /ygoblackjack et !ygoblackjack — Blackjack Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_game(self, channel: discord.abc.Messageable):
        deck = await fetch_monsters(self.session)
        if not deck:
            await safe_send(channel, "❌ Impossible de récupérer les cartes.")
            return

        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop()]

        view = BlackjackView(self.bot, self.session, player_cards, dealer_cards, deck)
        view.message = await safe_send(channel, "🃏 Blackjack YGO", view=view)
        await view.update_message(footer="Partie commencée !")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygoblackjack",
        description="Jouer au Blackjack avec des cartes Yu-Gi-Oh!"
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_ygoblackjack(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_game(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygoblackjack")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def prefix_ygoblackjack(self, ctx: commands.Context):
        await self._start_game(ctx.channel)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOBlackjack(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
