# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygoblackjack.py
# Objectif : Jouer au blackjack avec cartes Yu-Gi-Oh! (valeur = niveau des monstres)
# Catégorie : Minijeux
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
import random
import time

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Helper pour calculer la valeur blackjack d'une carte
# ────────────────────────────────────────────────────────────────────────────────
def card_value(level: int) -> int:
    """Retourne la valeur blackjack d'une carte (niveau)."""
    return level if level and level > 0 else 1

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fetch + cache des cartes monstres via YGOPRODeck (API v7)
# ────────────────────────────────────────────────────────────────────────────────
CACHE_TTL = 3600  # 1h — évite de retélécharger toute la base à chaque partie

async def fetch_monsters_pool(session):
    """Télécharge la liste complète des monstres niveau 1+ (une seule fois, mise en cache)."""
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"

    async with session.get(url) as resp:
        if resp.status != 200:
            print("[YGO BJ] HTTP error:", resp.status)
            return []

        data = await resp.json()

        if "data" not in data:
            print("[YGO BJ] API error:", data)
            return []

        monsters = [
            c for c in data["data"]
            if "Monster" in c.get("type", "")
            and c.get("level") is not None
            and c["level"] >= 1
        ]
        return monsters

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Blackjack interactif
# ────────────────────────────────────────────────────────────────────────────────
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
        """Seul le joueur qui a lancé la partie peut cliquer."""
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ta partie !", ephemeral=True
            )
            return False
        return True

    def _draw_card(self):
        """Pioche une carte, en repuisant dans le pool partagé si le deck local est vide."""
        if not self.deck:
            self.deck = self.cog.get_shuffled_pool()
        return self.deck.pop()

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

    # ────────────────────────────────────────────────────────────────────────────
    # 🃏 Bouton — Tirer
    # ────────────────────────────────────────────────────────────────────────────
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

    # ────────────────────────────────────────────────────────────────────────────
    # ✋ Bouton — Rester
    # ────────────────────────────────────────────────────────────────────────────
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

    # ────────────────────────────────────────────────────────────────────────────
    # ✋ clean boutons
    # ────────────────────────────────────────────────────────────────────────────
    async def on_timeout(self):
        """Appelé quand la vue expire (timeout de 120s)."""
        if self.game_over:
            return
        self.game_over = True
        for child in self.children:
            child.disabled = True
        if self.message:
            self.cog.active_channels.discard(self.message.channel.id)
            await safe_edit(self.message, view=self)


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class YGOBlackjack(commands.Cog):
    """Commande /ygoblackjack et !ygoblackjack — Blackjack Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pool = []          # cache des cartes monstres
        self._pool_fetched_at = 0
        self.active_channels = set()

    async def _get_pool(self):
        """Retourne le pool de cartes, en le retéléchargeant seulement si le cache est vide/périmé."""
        now = time.monotonic()
        if not self._pool or (now - self._pool_fetched_at) > CACHE_TTL:
            session = self.bot.aiohttp_session
            pool = await fetch_monsters_pool(session)
            if pool:
                self._pool = pool
                self._pool_fetched_at = now
        return self._pool

    def get_shuffled_pool(self):
        """Retourne une copie mélangée du cache pour piocher dedans (sync, appelé pendant la partie)."""
        pool = list(self._pool)
        random.shuffle(pool)
        return pool

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_game(self, channel: discord.abc.Messageable, author):
        if channel.id in self.active_channels:
            await safe_send(channel, "❌ Une partie est déjà en cours dans ce salon.")
            return

        pool = await self._get_pool()
        if not pool:
            await safe_send(channel, "❌ Impossible de récupérer les cartes.")
            return

        deck = self.get_shuffled_pool()
        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop()]

        view = BlackjackView(self, author.id, player_cards, dealer_cards, deck)
        self.active_channels.add(channel.id)
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
        await self._start_game(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygoblackjack", help="Jouer au Blackjack avec des cartes Yu-Gi-Oh!")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def prefix_ygoblackjack(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOBlackjack(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
