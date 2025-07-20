# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande interactive !akinator
# Objectif : Deviner une carte Yu-Gi-Oh! via questions Oui/Non/Je sais pas
# Catégorie : Yu-Gi-Oh
# Accès : Public
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

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des questions JSON enrichies (texte + filtre associé)
# ────────────────────────────────────────────────────────────────────────────────
DATA_QUESTIONS_PATH = os.path.join("data", "akiquestions.json")

def load_questions():
    with open(DATA_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive Akinator avec boutons Oui/Non/Je sais pas
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorView(View):
    def __init__(self, bot, ctx, all_cards, questions, message):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.all_cards = all_cards
        self.remaining = all_cards[:]  # cartes restantes possibles
        self.questions = questions
        self.message = message
        self.used_questions = []
        self.current_q = None
        self.max_questions = 10

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        await safe_edit(self.message, content="⏰ Temps écoulé.", embed=None, view=None)
        self.stop()

    async def update_question(self):
        # Fin si 1 carte ou max questions atteintes
        if len(self.remaining) <= 1 or len(self.used_questions) >= self.max_questions:
            await self.finish_game()
            return
        self.current_q = self.select_best_question()
        if not self.current_q:
            await self.finish_game()
            return
        self.used_questions.append(self.current_q)

        embed = discord.Embed(
            title=f"Question {len(self.used_questions)} / {self.max_questions}",
            description=self.current_q['text'],
            color=discord.Color.dark_gold()
        )
        await safe_edit(self.message, embed=embed, view=self)

    def select_best_question(self):
        best_q = None
        best_split = len(self.remaining)
        for q in self.questions:
            if q in self.used_questions:
                continue
            yes_count, no_count = 0, 0
            for card in self.remaining:
                if self.match_filter(card, q):
                    yes_count += 1
                else:
                    no_count += 1
            # Ignorer questions qui ne filtrent pas
            if yes_count == 0 or no_count == 0:
                continue
            max_split = max(yes_count, no_count)
            if max_split < best_split:
                best_split = max_split
                best_q = q
        return best_q

    def match_filter(self, card, question):
        key, value = question['filter_key'], question['filter_value']
        if key not in card:
            return False
        # Exemple de filtre simple (contient la valeur dans le champ)
        return value.lower() in str(card[key]).lower()

    async def process_answer(self, answer):
        if answer == "idk":
            # Ne filtre pas les cartes restantes
            pass
        else:
            filtered = []
            for card in self.remaining:
                match = self.match_filter(card, self.current_q)
                if (answer == "oui" and match) or (answer == "non" and not match):
                    filtered.append(card)
            self.remaining = filtered
            # Si plus aucune carte, on pourrait ici recharger l'échantillon en filtrant plus large
            if not self.remaining:
                await safe_edit(self.message, content="❌ Plus aucune carte ne correspond aux critères.", embed=None, view=None)
                self.stop()
                return
        await self.update_question()

    async def finish_game(self):
        if self.remaining:
            card = self.remaining[0]
            embed = discord.Embed(
                title="Je pense à cette carte !",
                description=f"**{card['name']}**",
                color=discord.Color.green()
            )
            # Si image dispo
            if 'card_images' in card and len(card['card_images']) > 0:
                embed.set_image(url=card['card_images'][0]['image_url'])
            await safe_edit(self.message, content=None, embed=embed, view=None)
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

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorCog(commands.Cog):
    """
    Commande !akinator — Devine une carte Yu-Gi-Oh! à laquelle tu penses.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.questions = load_questions()

    @commands.command(
        name="akinator",
        help="Devine une carte Yu-Gi-Oh! à laquelle tu penses.",
        description="Akinator version Yu-Gi-Oh!"
    )
    async def akinator(self, ctx: commands.Context):
        try:
            await safe_send(ctx, "🔍 Chargement des cartes...")
            async with aiohttp.ClientSession() as session:
                async with session.get("https://db.ygoprodeck.com/api/v7/cardinfo.php") as resp:
                    data = await resp.json()
                    cards = data.get("data", [])
            embed = discord.Embed(
                title="Akinator Yu-Gi-Oh!",
                description="Je vais deviner à quoi tu penses en 10 questions maximum.",
                color=discord.Color.dark_red()
            )
            msg = await safe_send(ctx, embed=embed)
            view = AkinatorView(self.bot, ctx, cards, self.questions, msg)
            await view.update_question()
        except Exception as e:
            await safe_send(ctx, f"❌ Une erreur est survenue : {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
