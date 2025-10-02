# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande interactive /akinator et !akinator
# Objectif : Deviner la carte Yu-Gi-Oh à laquelle pense le joueur via les critères avancés
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import aiohttp
import os
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Fichiers de questions et cache cartes
# ────────────────────────────────────────────────────────────────────────────────
QUESTIONS_JSON_PATH = "data/akinator_questions.json"
CACHE_PATH = "data/cards_cache.json"

def load_questions():
    try:
        with open(QUESTIONS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {QUESTIONS_JSON_PATH} : {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View pour Akinator
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorView(View):
    def __init__(self, bot, questions, cards):
        super().__init__(timeout=300)
        self.bot = bot
        self.questions = questions
        self.remaining_cards = cards
        self.message = None
        self.scores = {c["id"]: 0 for c in self.remaining_cards}
        self.current_question = None
        self.current_value = None
        self.question_count = 0

    def choose_best_question(self):
        """
        Sélectionne la question la plus discriminante.
        Priorité : éliminer ~50% des cartes restantes si possible.
        """
        best_q = None
        best_balance = float('inf')
        for q in self.questions:
            if not q.get("filter_value"):
                continue
            for val in q["filter_value"]:
                count = sum(1 for c in self.remaining_cards if val in c.get(q["filter_key"], []))
                balance = abs(len(self.remaining_cards)/2 - count)
                # On priorise les questions qui coupent au plus proche de la moitié
                if balance < best_balance:
                    best_balance = balance
                    best_q = q
                    self.current_value = val
        return best_q

    def next_question(self):
        if len(self.remaining_cards) <= 3 or not self.questions:
            return None
        self.current_question = self.choose_best_question()
        return self.current_question

    async def ask_question(self, interaction=None):
        # Au moins 10 questions avant de proposer une carte
        propose_card = self.question_count >= 10 and len(self.remaining_cards) <= 5

        q = None if propose_card else self.next_question()
        top_cards = sorted(self.remaining_cards, key=lambda c: self.scores[c["id"]], reverse=True)[:3]

        if not q:
            embed = discord.Embed(
                title="🔮 Résultat Akinator",
                description="\n".join(f"• {c['name']}" for c in top_cards),
                color=discord.Color.purple()
            )
            for c in top_cards:
                if "card_images" in c and c["card_images"]:
                    embed.set_image(url=c["card_images"][0]["image_url"])
                    break
            if interaction:
                await safe_edit(interaction.message, embed=embed, view=None)
            return embed

        self.clear_items()
        self.add_item(AkinatorButton(self, "Oui"))
        self.add_item(AkinatorButton(self, "Non"))
        self.add_item(AkinatorButton(self, "Ne sais pas"))
        self.add_item(AkinatorButton(self, "Abandonner", style=discord.ButtonStyle.danger))

        question_text = q["text"].replace("{value}", self.current_value or "…")
        embed = discord.Embed(
            title="❓ Question Akinator",
            description=f"{question_text}\n\n**Carte probable:** {top_cards[0]['name'] if top_cards else '…'}",
            color=discord.Color.blue()
        )
        if top_cards and "card_images" in top_cards[0] and top_cards[0]["card_images"]:
            embed.set_thumbnail(url=top_cards[0]["card_images"][0]["image_url_small"])

        if interaction:
            await safe_edit(interaction.message, embed=embed, view=self)
        else:
            return embed

    async def process_answer(self, answer: str, interaction: discord.Interaction):
        if answer == "Abandonner":
            embed = discord.Embed(
                title="🛑 Akinator abandonné",
                description="La session a été annulée.",
                color=discord.Color.red()
            )
            await safe_edit(interaction.message, embed=embed, view=None)
            return

        q = self.current_question
        val = self.current_value
        for c in self.remaining_cards:
            values = c.get(q["filter_key"], [])
            if answer == "Oui" and val in values:
                self.scores[c["id"]] += 1
            elif answer == "Non" and val in values:
                self.scores[c["id"]] -= 1

        if q in self.questions:
            self.questions.remove(q)

        min_score = min(self.scores.values())
        self.remaining_cards = [c for c in self.remaining_cards if self.scores[c["id"]] > min_score - 2]

        self.question_count += 1
        await self.ask_question(interaction)

class AkinatorButton(Button):
    def __init__(self, parent_view: AkinatorView, label: str, style=discord.ButtonStyle.primary):
        super().__init__(label=label, style=style)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.parent_view.process_answer(self.label, interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorCog(commands.Cog):
    """
    Commande /akinator et !akinator — Le bot devine la carte Yu-Gi-Oh
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cards_cache = None

    async def fetch_cards(self):
        if self.cards_cache:
            return self.cards_cache
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    self.cards_cache = json.load(f)
                    return self.cards_cache
            except Exception as e:
                print(f"[ERREUR CACHE] {e}")

        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                cards = []
                for c in data["data"]:
                    type_subtype = c.get("type", "").split()
                    if c.get("race"): type_subtype.append(c["race"])
                    attribute = [c["attribute"]] if c.get("attribute") else []
                    archetype = [c["archetype"]] if c.get("archetype") else []
                    effect = ["Effect"] if c.get("has_effect") else ["Normal"]
                    linkmarkers = c.get("linkmarkers") or []
                    cards.append({
                        "id": c.get("id"),
                        "name": c.get("name","Inconnue"),
                        "type_subtype": type_subtype,
                        "attribute": attribute,
                        "archetype": archetype,
                        "effect": effect,
                        "level": c.get("level"),
                        "atk": c.get("atk"),
                        "def": c.get("def"),
                        "linkval": c.get("linkval"),
                        "linkmarkers": linkmarkers,
                        "card_sets": c.get("card_sets"),
                        "card_images": c.get("card_images"),
                    })

        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cards, f, ensure_ascii=False, indent=4)
        self.cards_cache = cards
        return cards

    async def _send_akinator(self, channel: discord.abc.Messageable):
        questions = load_questions()
        if not questions:
            await safe_send(channel, "❌ Impossible de charger les questions Akinator.")
            return
        cards = await self.fetch_cards()
        if not cards:
            await safe_send(channel, "❌ Impossible de récupérer les cartes depuis l'API YGOPRODeck.")
            return
        view = AkinatorView(self.bot, questions, cards)
        embed = await view.ask_question()
        view.message = await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="akinator", description="Le bot devine la carte Yu-Gi-Oh à laquelle tu penses !")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_akinator(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            await self._send_akinator(interaction.channel)
            await interaction.delete_original_response()
        except Exception as e:
            print(f"[ERREUR /akinator] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="akinator")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_akinator(self, ctx: commands.Context):
        try:
            await self._send_akinator(ctx.channel)
        except Exception as e:
            print(f"[ERREUR !akinator] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
