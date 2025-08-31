# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande interactive /akinator et !akinator
# Objectif : Deviner la carte Yu-Gi-Oh à laquelle pense le joueur via l'API YGOPRODeck
# Catégorie : Fun
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
            content = "Je pense que ta carte pourrait être :\n" + "\n".join(f"• {c['name']}" for c in best_cards)
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
class Akinator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_cards(self):
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                cards = []
                for c in data['data']:
                    cards.append({
                        "id": c.get("id"),
                        "name": c.get("name"),
                        "type_subtype": [c.get("type")] + c.get("race", []).split() if c.get("race") else [c.get("type")],
                        "attribute": [c.get("attribute")] if c.get("attribute") else [],
                        "archetype": [c.get("archetype")] if c.get("archetype") else [],
                        "stats": [],
                        "effect": [c.get("type")]
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



aaaa

# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande interactive /akinator et !akinator
# Objectif : Deviner une carte Yu-Gi-Oh! via questions intelligentes Oui/Non/Je sais pas
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import json
import os
from utils.discord_utils import safe_send, safe_edit
import random

DATA_JSON_PATH = os.path.join("data", "akiquestions.json")

def load_questions():
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"[ERREUR JSON] Format invalide, attendu list : {DATA_JSON_PATH}")
                return []
            return data
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {DATA_JSON_PATH} : {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive Akinator avec boutons Oui/Non/Je sais pas
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorView(View):
    def __init__(self, bot, ctx, cards, questions, message=None):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.cards = cards if cards else []
        self.remaining = self.cards[:]
        self.questions = questions if questions else []
        self.message = message
        self.used_questions = []
        self.current_question = None
        self.max_questions = 20
        self.min_questions = 10  # minimum 10 questions avant proposition
        self.proposed_cards = set()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        try:
            await safe_edit(self.message, content="⏰ Temps écoulé.", embed=None, view=None)
        except:
            pass
        self.stop()

    async def start(self):
        if not self.cards:
            await safe_send(self.ctx, "❌ Impossible de charger les cartes.")
            self.stop()
            return
        if not self.message:
            embed = discord.Embed(
                title="Akinator Yu-Gi-Oh!",
                description="Chargement des cartes...",
                color=discord.Color.dark_red()
            )
            self.message = await safe_send(self.ctx, embed=embed)
        await self.ask_next_question()

    async def ask_next_question(self):
        self.remaining = [
            c for c in self.remaining
            if (c.get('id') or c.get('card_id') or c.get('name')) not in self.proposed_cards
        ]

        if len(self.remaining) <= 1 or len(self.used_questions) >= self.max_questions:
            if len(self.used_questions) >= self.min_questions:
                await self.finish_game()
                return

        self.current_question = self.select_best_question()
        if not self.current_question:
            # Choisir une question aléatoire si aucune "optimale"
            remaining_qs = [q for q in self.questions if q not in self.used_questions]
            if remaining_qs:
                self.current_question = random.choice(remaining_qs)
            else:
                if len(self.used_questions) >= self.min_questions:
                    await self.finish_game()
                    return
                else:
                    await safe_edit(self.message, content="⚠️ Plus de questions disponibles, mais le minimum de 10 questions n'est pas atteint.", embed=None, view=None)
                    self.stop()
                    return

        fv_list = self.current_question.get("filter_value", [])
        if not fv_list:
            fv_list = [""]  # valeur par défaut pour éviter crash
        self.current_question["current_value"] = random.choice(fv_list) if isinstance(fv_list, list) else fv_list

        question_text = self.current_question.get("text", "Question inconnue").replace("{value}", str(self.current_question["current_value"]))

        self.used_questions.append(self.current_question)

        embed = discord.Embed(
            title=f"Question {len(self.used_questions)} / {self.max_questions}",
            description=question_text,
            color=discord.Color.dark_gold()
        )
        await safe_edit(self.message, embed=embed, view=self)

    def select_best_question(self):
        best_q = None
        best_score = -1
        for q in self.questions:
            if q in self.used_questions:
                continue
            try:
                yes_count = sum(1 for c in self.remaining if self.match_filter(c, q))
                no_count = len(self.remaining) - yes_count
                score = min(yes_count, no_count)
                if score > best_score:
                    best_score = score
                    best_q = q
            except Exception:
                continue
        return best_q

    def match_filter(self, card, question):
        try:
            key = question.get('filter_key')
            value = question.get("current_value")
            if value is None or key not in card:
                return False
            if isinstance(value, list):
                return any(str(v).lower() in str(card[key]).lower() for v in value)
            return str(value).lower() in str(card[key]).lower()
        except Exception:
            return False

    async def process_answer(self, answer):
        try:
            if answer != "idk":
                self.remaining = [
                    c for c in self.remaining
                    if (answer == "oui" and self.match_filter(c, self.current_question)) or
                       (answer == "non" and not self.match_filter(c, self.current_question))
                ]
                if not self.remaining:
                    await safe_edit(self.message, content="❌ Plus aucune carte ne correspond aux critères.", embed=None, view=None)
                    self.stop()
                    return
            await self.ask_next_question()
        except Exception as e:
            await safe_edit(self.message, content=f"❌ Une erreur est survenue : {e}", embed=None, view=None)
            self.stop()

    async def finish_game(self):
        try:
            if self.remaining:
                card = self.remaining[0]
                card_id = card.get('id') or card.get('card_id') or card.get('name')
                if card_id:
                    self.proposed_cards.add(card_id)
                    self.remaining = [
                        c for c in self.remaining
                        if (c.get('id') or c.get('card_id') or c.get('name')) != card_id
                    ]

                embed = discord.Embed(
                    title="Je pense à cette carte !",
                    description=f"**{card.get('name', 'Carte inconnue')}**\nEst-ce bien ta carte ?",
                    color=discord.Color.green()
                )
                if 'card_images' in card and card['card_images']:
                    embed.set_image(url=card['card_images'][0].get('image_url', ''))

                await safe_edit(self.message, content=None, embed=embed, view=ConfirmGuessView(self))
            else:
                await safe_edit(self.message, content="❌ Je n'ai pas trouvé de carte correspondante.", embed=None, view=None)
                self.stop()
        except Exception as e:
            await safe_edit(self.message, content=f"❌ Une erreur est survenue : {e}", embed=None, view=None)
            self.stop()

    @discord.ui.button(label="Oui", style=discord.ButtonStyle.success)
    async def yes(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.process_answer("oui")

    @discord.ui.button(label="Non", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.process_answer("non")

    @discord.ui.button(label="Je sais pas", style=discord.ButtonStyle.secondary)
    async def idk(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.process_answer("idk")


# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive pour confirmer la carte
# ────────────────────────────────────────────────────────────────────────────────
class ConfirmGuessView(View):
    def __init__(self, akinator_view):
        super().__init__(timeout=60)
        self.akinator_view = akinator_view

    @discord.ui.button(label="Oui, c'est la bonne carte", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.followup.send(
                content="🎉 **Super ! J'ai trouvé ta carte !** Merci d'avoir joué à Akinator Yu-Gi-Oh!",
                ephemeral=False
            )
            await interaction.message.edit(view=None)
            self.akinator_view.stop()
        except:
            pass

    @discord.ui.button(label="Non, essaie encore", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.defer()
            self.akinator_view.max_questions += 20
            self.akinator_view.used_questions = []
            await safe_edit(self.akinator_view.message, embed=None, view=self.akinator_view)
            await self.akinator_view.ask_next_question()
        except:
            pass


# ────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────
class AkinatorCog(commands.Cog):
    """
    Commande /akinator et !akinator — Devine une carte Yu-Gi-Oh!
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.questions = load_questions()

    @commands.command(name="akinator", help="Devine une carte Yu-Gi-Oh! à laquelle tu penses.")
    async def akinator(self, ctx: commands.Context):
        try:
            await safe_send(ctx, "🔍 Chargement des cartes...")
            async with aiohttp.ClientSession() as session:
                async with session.get("https://db.ygoprodeck.com/api/v7/cardinfo.php") as resp:
                    if resp.status != 200:
                        await safe_send(ctx, f"❌ Impossible de récupérer les cartes, code {resp.status}")
                        return
                    data = await resp.json()
                    cards = data.get("data", [])
            if not cards:
                await safe_send(ctx, "❌ Aucune carte trouvée.")
                return

            view = AkinatorView(self.bot, ctx, cards, self.questions)
            await view.start()
        except Exception as e:
            await safe_send(ctx, f"❌ Une erreur est survenue : {e}")


# ────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
