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
# 🎛️ UI — Vue interactive pour questions avec boutons Oui/Non/Je sais pas
# ────────────────────────────────────────────────────────────────────────────────
class AkinatorView(View):
    def __init__(self, bot, ctx, questions):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.questions = questions
        self.question_num = 0
        self.filters = {}
        self.answers = []
        self.card_candidates = None

    async def send_next_question(self):
        if self.question_num < len(self.questions):
            question = self.questions[self.question_num]
            embed = discord.Embed(title=f"Question {self.question_num + 1}", description=question, color=discord.Color.blue())
            await safe_send(self.ctx.channel, embed=embed, view=self)
        else:
            # Dès la 6e question, on charge les cartes filtrées (limité à 100)
            await self.load_cards()
            if self.card_candidates:
                card = self.card_candidates[0]
                await safe_send(self.ctx.channel, f"Je pense que c'est : **{card['name']}**")
            else:
                await safe_send(self.ctx.channel, "❌ Je n'ai pas réussi à trouver une carte correspondant aux critères.")
            self.stop()

    async def load_cards(self):
        base_url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        params = []

        # Exemple simple : on traduit les filtres en paramètres API
        # Ici, il faudra faire un mapping plus complet selon les filtres
        # Pour exemple, on gère juste type et race
        if "type" in self.filters:
            if self.filters["type"] == "Monster":
                params.append("type=Monster")
            elif self.filters["type"] == "SpellTrap":
                params.append("type=Spell,Trap")

        if "race" in self.filters:
            params.append(f"race={self.filters['race']}")

        # Autres filtres (ex: atk_min) à implémenter si besoin

        params.append("num=100")  # Limite à 100 cartes max

        url = base_url + "?" + "&".join(params)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.card_candidates = data.get("data", [])
                else:
                    self.card_candidates = []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        await safe_send(self.ctx.channel, "⏰ Temps écoulé, la partie est terminée.")
        self.stop()

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

    async def process_answer(self, answer):
        q = self.questions[self.question_num]

        # Exemple simplifié de filtrage basé sur la question et la réponse
        # Tu peux créer un mapping question->filtre dans un dict pour plus de clarté
        if "monstre" in q.lower() and self.question_num == 0:
            if answer == "oui":
                self.filters["type"] = "Monster"
            elif answer == "non":
                self.filters["type"] = "SpellTrap"
        else:
            # Exemple basique pour détecter les races dans la question
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
        await self.send_next_question()

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
        name="akinator",
        help="Deviner une carte Yu-Gi-Oh! via questions Oui/Non/Je sais pas.",
        description="Pose des questions pour deviner la carte à laquelle tu penses."
    )
    async def akinator(self, ctx: commands.Context):
        """Commande principale !akinator avec interface interactive boutons."""
        try:
            view = AkinatorView(self.bot, ctx, self.questions)
            await safe_send(ctx.channel, "Je vais essayer de deviner la carte à laquelle tu penses. Réponds par Oui / Non / Je sais pas.", view=view)
            await view.send_next_question()
        except Exception as e:
            print(f"[ERREUR akinator] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors du lancement de la partie.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Yu-Gi-Oh"
    await bot.add_cog(cog)
