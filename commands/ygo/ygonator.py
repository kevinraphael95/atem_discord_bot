# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande interactive !akinator
# Objectif : Deviner une carte Yu-Gi-Oh! via questions Oui/Non/Je sais pas en filtrant l’API YGOPRODeck avec 50 questions JSON
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
import random

from utils.discord_utils import safe_send, safe_edit, safe_respond

DATA_QUESTIONS_PATH = os.path.join("data", "akiquestions.json")


def load_questions():
    with open(DATA_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class AkinatorView(View):
    def __init__(self, bot, ctx, all_cards, questions, message):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.all_cards = all_cards
        self.remaining = all_cards[:]
        self.questions = questions
        self.message = message
        self.used_questions = []
        self.filters_applied = []  # historique des filtres
        self.current_q = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        await safe_edit(self.message, content="⏰ Temps écoulé.", embed=None, view=None)
        self.stop()

    async def update_question(self):
        if len(self.remaining) <= 1 or len(self.used_questions) >= len(self.questions):
            await self.finish_game()
            return

        self.current_q = self.select_best_question()
        if not self.current_q:
            await self.finish_game()
            return

        self.used_questions.append(self.current_q)
        embed = discord.Embed(
            title=f"Question {len(self.used_questions)}",
            description=self.current_q['text'],
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text=f"{len(self.remaining)} carte(s) restante(s)")
        await safe_edit(self.message, embed=embed, view=self)

    def select_best_question(self):
        best_q = None
        best_split = len(self.remaining)
        for q in self.questions:
            if q in self.used_questions:
                continue
            yes, no = 0, 0
            for c in self.remaining:
                if self.match_filter(c, q):
                    yes += 1
                else:
                    no += 1
            if yes + no == 0:
                continue  # question inutile
            max_split = max(yes, no)
            if max_split < best_split:
                best_split = max_split
                best_q = q
        return best_q

    def match_filter(self, card, question):
        key, value = question['filter_key'], question['filter_value']
        if key not in card:
            return False
        return value.lower() in str(card[key]).lower()

    async def process_answer(self, answer):
        if answer == "idk":
            pass
        else:
            self.filters_applied.append((self.current_q, answer))
            keep = []
            for c in self.remaining:
                match = self.match_filter(c, self.current_q)
                if (answer == "oui" and match) or (answer == "non" and not match):
                    keep.append(c)
            self.remaining = keep

        if not self.remaining:
            await self.refetch_filtered_cards()
        await self.update_question()

    async def refetch_filtered_cards(self):
        async with aiohttp.ClientSession() as session:
            url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?"
            query_params = []
            for q, a in self.filters_applied:
                if a == "oui":
                    query_params.append(f"{q['filter_key']}={q['filter_value']}")
            full_url = url + "&".join(query_params) if query_params else url
            async with session.get(full_url) as resp:
                data = await resp.json()
                new_cards = data.get("data", [])

        # Filtrage des non
        for q, a in self.filters_applied:
            if a == "non":
                new_cards = [
                    c for c in new_cards
                    if not self.match_filter(c, q)
                ]

        self.remaining = new_cards

    async def finish_game(self):
        if self.remaining:
            card = self.remaining[0]
            embed = discord.Embed(
                title="🧠 Je pense à...",
                description=f"**{card['name']}**",
                color=discord.Color.green()
            )
            if 'card_images' in card and card['card_images']:
                embed.set_image(url=card['card_images'][0]['image_url'])
            await safe_edit(self.message, embed=embed, view=None)
        else:
            await safe_edit(self.message, content="❌ Je n'ai pas trouvé la carte.", embed=None, view=None)
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


class AkinatorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.questions = load_questions()

    @commands.command(name="akinator", help="Devine une carte Yu-Gi-Oh! à laquelle tu penses.")
    async def akinator(self, ctx: commands.Context):
        try:
            await safe_send(ctx, "🔍 Chargement des cartes...")
            async with aiohttp.ClientSession() as session:
                async with session.get("https://db.ygoprodeck.com/api/v7/cardinfo.php?num=300") as resp:
                    data = await resp.json()
                    cards = data.get("data", [])
            embed = discord.Embed(
                title="Akinator Yu-Gi-Oh!",
                description="Pense à une carte Yu-Gi-Oh!, je vais deviner laquelle en 10 questions maximum.",
                color=discord.Color.dark_red()
            )
            msg = await safe_send(ctx, embed=embed)
            view = AkinatorView(self.bot, ctx, cards, self.questions, msg)
            await view.update_question()
        except Exception as e:
            await safe_send(ctx, f"❌ Une erreur est survenue : {e}")


────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
