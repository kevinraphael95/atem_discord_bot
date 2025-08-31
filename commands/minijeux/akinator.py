# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande interactive /akinator et !akinator
# Objectif : Deviner la carte Yu-Gi-Oh à laquelle pense le joueur via l'API YGOPRODeck
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
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
QUESTIONS_JSON_PATH = "data/akinator_questions.json"

def load_questions():
    try:
        with open(QUESTIONS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {QUESTIONS_JSON_PATH} : {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View intelligente avec boutons Oui / Non / Ne sais pas
# ────────────────────────────────────────────────────────────────────────────────
class IntelligentQuestionView(View):
    def __init__(self, bot, questions, cards):
        super().__init__(timeout=120)
        self.bot = bot
        self.questions = questions
        self.remaining_cards = cards
        self.message = None
        self.current_question = None
        self.scores = {c['id']: 0 for c in self.remaining_cards}
        self.next_question()

    def most_discriminant_question(self):
        """Choisit la question qui divise le mieux les cartes restantes."""
        best_q = None
        best_score = -1
        for q in self.questions:
            counts = []
            for val in q["filter_value"]:
                count = sum(1 for c in self.remaining_cards if val in c.get(q["filter_key"], []))
                counts.append(count)
            if not counts:
                continue
            score = min(counts)
            if score > best_score:
                best_score = score
                best_q = q
        return best_q

    def next_question(self):
        if not self.questions or len(self.remaining_cards) <= 3:
            return None
        self.current_question = self.most_discriminant_question()
        return self.current_question

    async def ask_question(self, interaction=None):
        q = self.next_question()
        if not q:
            # Affiche le résultat
            best_cards = sorted(self.remaining_cards, key=lambda c: self.scores[c['id']], reverse=True)[:3]
            content = "🔮 Je pense que ta carte pourrait être :\n" + "\n".join(f"• {c['name']}" for c in best_cards)
            if interaction:
                await safe_edit(interaction.message, content=content, view=None)
            return

        self.clear_items()
        # Trois boutons : Oui / Non / Ne sais pas
        self.add_item(AnswerButton(self, "Oui"))
        self.add_item(AnswerButton(self, "Non"))
        self.add_item(AnswerButton(self, "Ne sais pas"))

        content = q["text"].replace("{value}", "...")
        if interaction:
            await safe_edit(interaction.message, content=content, view=self)
        else:
            return content

    async def process_answer(self, answer: str, interaction: discord.Interaction):
        q = self.current_question
        for c in self.remaining_cards:
            values = c.get(q["filter_key"], [])
            if answer == "Oui" and any(v in values for v in q["filter_value"]):
                self.scores[c['id']] += 1
            elif answer == "Non" and any(v in values for v in q["filter_value"]):
                self.scores[c['id']] -= 1
            # "Ne sais pas" ne change pas le score

        if q in self.questions:
            self.questions.remove(q)
        await self.ask_question(interaction)

class AnswerButton(Button):
    def __init__(self, parent_view: IntelligentQuestionView, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.process_answer(self.label, interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_cards(self):
        """Récupère les cartes depuis l’API YGOPRODeck et les prépare pour l’Akinator."""
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                cards = []
                for c in data['data']:
                    cards.append({
                        "id": c.get("id"),
                        "name": c.get("name"),
                        "type_subtype": [c.get("type")] + ([c.get("race")] if c.get("race") else []),
                        "attribute": [c.get("attribute")] if c.get("attribute") else [],
                        "archetype": [c.get("archetype")] if c.get("archetype") else [],
                        "stats": [
                            f"ATK>={c.get('atk')}" if c.get("atk") else None,
                            f"DEF>={c.get('def')}" if c.get("def") else None,
                            f"Level>={c.get('level')}" if c.get("level") else None,
                        ],
                        "effect": [c.get("type")]  # simplifié, on pourra l’enrichir
                    })
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

        view = IntelligentQuestionView(self.bot, questions, cards)
        content = await view.ask_question()
        view.message = await safe_send(channel, content=content, view=view)

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
