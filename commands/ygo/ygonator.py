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
from utils.discord_utils import safe_send, safe_edit, safe_respond  # ✅ Utilisation des safe_

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des questions JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_QUESTIONS_PATH = os.path.join("data", "akiquestions.json")

def load_questions():
    with open(DATA_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue interactive avec boutons Oui / Non / Je sais pas
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorView(View):
    def __init__(self, bot, ctx, questions, message):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.questions = questions
        self.message = message
        self.question_num = 0
        self.filters = {}
        self.answers = []
        self.card_candidates = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        await safe_edit(self.message, content="⏰ Temps écoulé, la partie est terminée.", embed=None, view=None)
        self.stop()

    async def update_embed(self):
        embed = discord.Embed(
            title=f"Question {self.question_num + 1}",
            description=self.questions[self.question_num],
            color=discord.Color.blue()
        )
        await safe_edit(self.message, embed=embed, view=self)

    async def finish_game(self):
        await self.load_cards()
        if self.card_candidates:
            card = self.card_candidates[0]
            await safe_edit(self.message, content=f"🧠 Je pense que c'est : **{card['name']}**", embed=None, view=None)
        else:
            await safe_edit(self.message, content="❌ Je n'ai pas trouvé de carte correspondant aux réponses.", embed=None, view=None)
        self.stop()

    async def load_cards(self):
        base_url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        params = []

        if "type" in self.filters:
            if self.filters["type"] == "Monster":
                params.append("type=Normal Monster,Effect Monster,Fusion Monster,Synchro Monster,Xyz Monster,Ritual Monster,Link Monster")
            elif self.filters["type"] == "SpellTrap":
                params.append("type=Spell Card,Trap Card")

        if "race" in self.filters:
            params.append(f"race={self.filters['race']}")

        params.append("num=100")  # max 100 cartes

        url = base_url + "?" + "&".join(params)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.card_candidates = data.get("data", [])
                else:
                    self.card_candidates = []

    async def process_answer(self, answer):
        q = self.questions[self.question_num]

        if "monstre" in q.lower() and self.question_num == 0:
            if answer == "oui":
                self.filters["type"] = "Monster"
            elif answer == "non":
                self.filters["type"] = "SpellTrap"
        else:
            races = ["dragon", "guerrier", "magicien", "machine", "zombie", "bête", "bête ailée",
                     "dinosaure", "elfe", "psy", "aqua", "roche", "insecte", "serpent de mer", "plante", "tonnerre",
                     "pyro", "démon", "ange"]
            for race in races:
                if race in q.lower():
                    if answer == "oui":
                        self.filters["race"] = race.capitalize()
                    break

        self.answers.append(answer)
        self.question_num += 1

        if self.question_num >= 5:
            await self.finish_game()
        else:
            await self.update_embed()

    @discord.ui.button(label="Oui", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.process_answer("oui")

    @discord.ui.button(label="Non", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.process_answer("non")

    @discord.ui.button(label="Je sais pas", style=discord.ButtonStyle.grey)
    async def idk(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.process_answer("je sais pas")

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorCog(commands.Cog):
    """
    Commande !akinator — Deviner une carte Yu-Gi-Oh! via questions Oui/Non/Je sais pas chargées depuis un JSON.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.questions = load_questions()

    @commands.command(
        name="akinator", aliases=["ygonator"],
        help="Devine une carte Yu-Gi-Oh! en posant des questions Oui/Non/Je sais pas.",
        description="Pose des questions pour deviner à quoi tu penses."
    )
    async def akinator(self, ctx: commands.Context):
        """Commande principale !akinator avec questions sur un seul message."""
        try:
            embed = discord.Embed(
                title="Question 1",
                description=self.questions[0],
                color=discord.Color.blue()
            )
            msg = await safe_send(ctx.channel, "Je vais essayer de deviner à quoi tu penses.", embed=embed)
            view = AkinatorView(self.bot, ctx, self.questions, msg)
            await msg.edit(view=view)
        except Exception as e:
            print(f"[ERREUR akinator] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue pendant la partie.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
