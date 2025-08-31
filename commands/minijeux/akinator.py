# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande interactive /akinator et !akinator
# Objectif : Deviner une carte Yu-Gi-Oh! via questions intelligentes Oui/Non/Je sais pas
# Catégorie : Yu-Gi-Oh
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import json
import os
from utils.discord_utils import safe_send, safe_edit

DATA_JSON_PATH = os.path.join("data", "akiquestions.json")

def load_questions():
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {DATA_JSON_PATH} : {e}")
        return []

class AkinatorView(View):
    def __init__(self, bot, ctx, cards, questions, message=None):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.cards = cards
        self.remaining = cards[:]
        self.questions = questions
        self.message = message
        self.used_questions = []
        self.current_question = None
        self.max_questions = 20
        self.proposed_cards = set()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        await safe_edit(self.message, content="⏰ Temps écoulé.", embed=None, view=None)
        self.stop()

    async def start(self):
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
            await self.finish_game()
            return

        # Sélection intelligente
        self.current_question = self.select_best_question()
        if not self.current_question:
            await self.finish_game()
            return

        question_data = self.current_question

        # Définir filter_value si pas encore fait
        import random
        if "filter_value" not in question_data:
            if "options" in question_data:
                question_data["filter_value"] = random.choice(question_data["options"])
            elif "ranges" in question_data:
                question_data["filter_value"] = random.choice(question_data["ranges"])

        # Générer texte de question
        fv = question_data["filter_value"]
        question_text = question_data.get("prompt", "")
        if isinstance(fv, dict):
            question_text = question_text.replace("{min}", str(fv["min"])).replace("{max}", str(fv["max"]))
        else:
            question_text = question_text.replace("{value}", str(fv))

        question_data["text"] = question_text
        self.used_questions.append(question_data)

        embed = discord.Embed(
            title=f"Question {len(self.used_questions)} / {self.max_questions}",
            description=question_text,
            color=discord.Color.dark_gold()
        )
        await safe_edit(self.message, embed=embed, view=self)

    def select_best_question(self):
        best_q = None
        best_score = -1
        for q in self.questions.values():
            if q in self.used_questions:
                continue
            yes_count = sum(1 for c in self.remaining if self.match_filter(c, q))
            no_count = len(self.remaining) - yes_count
            if yes_count == 0 or no_count == 0:
                continue
            score = min(yes_count, no_count)
            if score > best_score:
                best_score = score
                best_q = q
        return best_q

    def match_filter(self, card, question):
        key = question['filter_key']
        value = question['filter_value']
        if key not in card:
            return False
        if isinstance(value, dict):
            return value["min"] <= card.get(key, 0) <= value["max"]
        return str(value).lower() in str(card[key]).lower()

    async def process_answer(self, answer):
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

    async def finish_game(self):
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
                description=f"**{card['name']}**\nEst-ce bien ta carte ?",
                color=discord.Color.green()
            )
            if 'card_images' in card and card['card_images']:
                embed.set_image(url=card['card_images'][0]['image_url'])

            await safe_edit(self.message, content=None, embed=embed, view=ConfirmGuessView(self))
        else:
            await safe_edit(self.message, content="❌ Je n'ai pas trouvé de carte correspondante.", embed=None, view=None)
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


class ConfirmGuessView(View):
    def __init__(self, akinator_view):
        super().__init__(timeout=60)
        self.akinator_view = akinator_view

    @discord.ui.button(label="Oui, c'est la bonne carte", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.followup.send(
            content="🎉 **Super ! J'ai trouvé ta carte !** Merci d'avoir joué à Akinator Yu-Gi-Oh!",
            ephemeral=False
        )
        await interaction.message.edit(view=None)
        self.akinator_view.stop()

    @discord.ui.button(label="Non, essaie encore", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.akinator_view.max_questions += 20
        self.akinator_view.used_questions = []
        await safe_edit(self.akinator_view.message, embed=None, view=self.akinator_view)
        await self.akinator_view.ask_next_question()


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
                    data = await resp.json()
                    cards = data.get("data", [])

            view = AkinatorView(self.bot, ctx, cards, self.questions)
            await view.start()
        except Exception as e:
            await safe_send(ctx, f"❌ Une erreur est survenue : {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
