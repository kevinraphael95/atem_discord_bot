# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygoblackjack.py
# Objectif : Jouer au blackjack avec les cartes Yu-Gi-Oh! (valeur = niveau)
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
# 🔹 Helper pour calculer la valeur de blackjack d’une carte
# ────────────────────────────────────────────────────────────────────────────────
def card_value(level: int) -> int:
    """Convertit le niveau d'une carte en valeur blackjack."""
    return level if level and level >= 1 else 1

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fetch un lot de cartes monstres (50 max) niveau ≥1
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_monster_batch(session: aiohttp.ClientSession, limit: int = 50):
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?type=Monster&language=fr"
    async with session.get(url) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()
        cards = data.get("data", [])
        monsters = [c for c in cards if c.get("level") and c["level"] >= 1]
        random.shuffle(monsters)
        return monsters[:limit]

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Blackjack interactif
# ────────────────────────────────────────────────────────────────
class BlackjackView(View):
    def __init__(self, bot, card_pool, player_cards, dealer_cards):
        super().__init__(timeout=120)
        self.bot = bot
        self.card_pool = card_pool
        self.player_cards = player_cards
        self.dealer_cards = dealer_cards
        self.message = None
        self.game_over = False
        self.restocking = False

    async def draw_card(self):
        """Tire une carte depuis le pool, recharge si nécessaire"""
        if not self.card_pool:
            self.restocking = True
            await self.message.channel.send("🔄 Stock vide, récupération d’un nouveau lot...")
            await asyncio.sleep(1)
            self.card_pool.extend(await fetch_monster_batch(self.bot.session, 50))
            self.restocking = False
        return self.card_pool.pop()

    async def update_embed(self, hide_dealer_card: bool = True, footer: str = None):
        """Met à jour l'embed avec la main du joueur et du dealer"""
        player_total = sum(card_value(c["level"]) for c in self.player_cards)
        if hide_dealer_card:
            dealer_total = card_value(self.dealer_cards[0]["level"])
            dealer_text = f"{self.dealer_cards[0]['name']} - Niveau {self.dealer_cards[0]['level']}\n🂠 Carte cachée"
        else:
            dealer_total = sum(card_value(c["level"]) for c in self.dealer_cards)
            dealer_text = "\n".join(f"{c['name']} - Niveau {c['level']}" for c in self.dealer_cards)

        embed = discord.Embed(title="🃏 Blackjack YGO", color=discord.Color.blue())
        embed.add_field(
            name="Tes cartes",
            value="\n".join(f"{c['name']} - Niveau {c['level']}" for c in self.player_cards) + f"\n**Total : {player_total}**",
            inline=False
        )
        embed.add_field(
            name="Cartes du dealer",
            value=f"{dealer_text}\n**Total visible : {dealer_total}**" if hide_dealer_card else f"{dealer_text}\n**Total : {dealer_total}**",
            inline=False
        )
        if footer:
            embed.set_footer(text=footer)
        await self.message.edit(embed=embed, view=self)

    async def end_game(self, msg: str):
        self.game_over = True
        for child in self.children:
            child.disabled = True
        await self.update_embed(hide_dealer_card=False, footer=msg)

    # ── Bouton Tirer 🃏 ──
    @discord.ui.button(label="Tirer 🃏", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: Button):
        if self.game_over or self.restocking:
            return
        card = await self.draw_card()
        self.player_cards.append(card)
        total = sum(card_value(c["level"]) for c in self.player_cards)
        if total > 21:
            await self.end_game("💀 Bust ! Tu as dépassé 21.")
        else:
            await self.update_embed(footer=f"Tu as tiré : {card['name']} - Niveau {card['level']}")
            await interaction.response.defer()

    # ── Bouton Rester ✋ ──
    @discord.ui.button(label="Rester ✋", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if self.game_over or self.restocking:
            return
        while sum(card_value(c["level"]) for c in self.dealer_cards) < 17:
            card = await self.draw_card()
            self.dealer_cards.append(card)

        player_total = sum(card_value(c["level"]) for c in self.player_cards)
        dealer_total = sum(card_value(c["level"]) for c in self.dealer_cards)
        if dealer_total > 21 or player_total > dealer_total:
            result = "🏆 Tu gagnes !"
        elif player_total < dealer_total:
            result = "😢 Tu perds !"
        else:
            result = "⚖️ Égalité !"
        await self.end_game(f"🛑 Tu as choisi de rester. {result}")

# ────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec cooldowns centralisés
# ────────────────────────────────────────────────────────────────
class NomDeLaCommande(commands.Cog):
    """
    Commande /ygoblackjack et !ygoblackjack — Jouer au blackjack YGO
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.card_pool = []

    # ────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────
    async def load_card_pool(self):
        if not self.card_pool:
            self.card_pool.extend(await fetch_monster_batch(self.session, 50))

    async def draw_card_from_pool(self):
        if not self.card_pool:
            self.card_pool.extend(await fetch_monster_batch(self.session, 50))
        return self.card_pool.pop()

    # ────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygoblackjack",
        description="Joue au blackjack avec des cartes Yu-Gi-Oh!"
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_ygoblackjack(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.load_card_pool()
        if not self.card_pool:
            await interaction.followup.send("❌ Impossible de récupérer les cartes.")
            return

        player_cards = [await self.draw_card_from_pool() for _ in range(2)]
        dealer_cards = [await self.draw_card_from_pool() for _ in range(1)]

        view = BlackjackView(self.bot, self.card_pool, player_cards, dealer_cards)
        view.message = await interaction.followup.send("🃏 Blackjack YGO — Partie commencée !")
        await view.update_embed(hide_dealer_card=True)
        await view.message.edit(view=view)

    # ────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────
    @commands.command(name="ygoblackjack")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_ygoblackjack(self, ctx: commands.Context):
        await self.load_card_pool()
        if not self.card_pool:
            await ctx.send("❌ Impossible de récupérer les cartes.")
            return

        player_cards = [await self.draw_card_from_pool() for _ in range(2)]
        dealer_cards = [await self.draw_card_from_pool() for _ in range(1)]

        view = BlackjackView(self.bot, self.card_pool, player_cards, dealer_cards)
        view.message = await ctx.send("🃏 Blackjack YGO — Partie commencée !")
        await view.update_embed(hide_dealer_card=True)
        await view.message.edit(view=view)

    # ────────────────────────────────────────────────────────────
    # 🔹 Cog unload
    # ────────────────────────────────────────────────────────────
    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

# ────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = NomDeLaCommande(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
