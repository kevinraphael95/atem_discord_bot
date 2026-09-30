# ================================================================================
# 📌 ygoblackjack.py
# Objectif : Jouer au blackjack avec cartes Yu-Gi-Oh! (valeur = niveau des monstres)
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 10s
# Version optimisée : utilise card_utils (0 RAM permanente)
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import random

from utils.discord_utils import safe_send, safe_edit
from utils.card_utils import fetch_cards_by_type

# ================================================================================
# 🔹 Helper pour calculer la valeur blackjack d'une carte
# ================================================================================
def card_value(level: int) -> int:
    """Retourne la valeur blackjack d'une carte (niveau)."""
    return level if level and level > 0 else 1

# ================================================================================
# 🎛️ UI — Blackjack interactif
# ================================================================================
class BlackjackView(View):
    def __init__(self, cog, player_id, player_cards, dealer_cards, deck):
        super().__init__(timeout=120)
        self.cog = cog
        self.player_id = player_id
        self.player_cards = player_cards
        self.dealer_cards = dealer_cards
        self.deck = deck
        self.message = None
        self.game_over = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ta partie !", ephemeral=True
            )
            return False
        return True

    def _draw_card(self):
        """Pioche une carte, en repuisant si le deck local est vide."""
        if not self.deck:
            self.deck = self.cog.get_shuffled_pool()
        return self.deck.pop()

    async def update_message(self, footer: str | None = None):
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
        self.game_over = True
        for child in self.children:
            child.disabled = True
        self.cog.active_channels.discard(self.message.channel.id if self.message else None)

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

    @discord.ui.button(label="Tirer 🃏", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        if self.game_over:
            return

        card = self._draw_card()
        self.player_cards.append(card)

        total = sum(card_value(c["level"]) for c in self.player_cards)
        if total > 21:
            await self.end_game("💀 Bust ! Tu as dépassé 21.")
        else:
            await self.update_message(
                footer=f"Tu as tiré : {card['name']} (Niveau {card['level']})"
            )

    @discord.ui.button(label="Rester ✋", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        if self.game_over:
            return

        while sum(card_value(c["level"]) for c in self.dealer_cards) < 17:
            self.dealer_cards.append(self._draw_card())

        player_total = sum(card_value(c["level"]) for c in self.player_cards)
        dealer_total = sum(card_value(c["level"]) for c in self.dealer_cards)

        if dealer_total > 21 or player_total > dealer_total:
            result = "🏆 Tu gagnes !"
        elif player_total < dealer_total:
            result = "😢 Tu perds !"
        else:
            result = "⚖️ Égalité !"

        await self.end_game(result)

    async def on_timeout(self):
        if self.game_over:
            return
        self.game_over = True
        for child in self.children:
            child.disabled = True
        if self.message:
            self.cog.active_channels.discard(self.message.channel.id)
            await safe_edit(self.message, view=self)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class YGOBlackjack(commands.Cog):
    """Commande /ygoblackjack et !ygoblackjack — Blackjack Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pool = []          # pool de 100 monstres (rafraîchi à chaque partie)
        self.active_channels = set()

    async def _get_pool(self):
        """Charge 100 monstres aléatoires (1 appel API)."""
        session = getattr(self.bot, "aiohttp_session", None)
        if not session or session.closed:
            return []

        # ✅ Charge 100 monstres (1 appel API + sample)
        cards = await fetch_cards_by_type(session, "Monster", n=100)

        # Filtre : garde uniquement ceux avec un niveau >= 1
        monsters = [
            c for c in cards
            if "Monster" in c.get("type", "")
            and c.get("level") is not None
            and c["level"] >= 1
        ]
        return monsters

    def get_shuffled_pool(self):
        """Mélange le pool actuel."""
        pool = list(self._pool)
        random.shuffle(pool)
        return pool

    async def _start_game(self, channel: discord.abc.Messageable, author):
        if channel.id in self.active_channels:
            await safe_send(channel, "❌ Une partie est déjà en cours dans ce salon.")
            return

        # ✅ Recharge un pool frais (1 appel API)
        pool = await self._get_pool()
        if len(pool) < 10:
            await safe_send(channel, "❌ Impossible de récupérer assez de cartes.")
            return

        self._pool = pool
        deck = self.get_shuffled_pool()
        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop()]

        view = BlackjackView(self, author.id, player_cards, dealer_cards, deck)
        self.active_channels.add(channel.id)
        view.message = await safe_send(channel, "🃏 Blackjack YGO", view=view)
        await view.update_message(footer="Partie commencée !")

    @app_commands.command(
        name="ygoblackjack",
        description="Jouer au Blackjack avec des cartes Yu-Gi-Oh!"
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_ygoblackjack(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_game(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    @commands.command(name="ygoblackjack", help="Jouer au Blackjack avec des cartes Yu-Gi-Oh!")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def prefix_ygoblackjack(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = YGOBlackjack(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
