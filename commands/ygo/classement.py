# ────────────────────────────────────────────────────────────────────────────────
# 📌 classement.py — Commande interactive !classement
# Objectif : Afficher le classement des joueurs par saison avec menu déroulant
# Catégorie : Yu-Gi-Oh
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# 📦 Imports nécessaires
import discord
from discord.ext import commands
from discord.ui import View, Select
import json
import os
from utils.discord_utils import safe_send, safe_edit

# 📂 Chargement des données JSON
DATA_JSON_PATH = os.path.join("data", "classement.json")

def load_data():
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# 🎛️ UI — Menu de sélection de saison
class SaisonSelectView(View):
    def __init__(self, bot, data):
        super().__init__(timeout=120)
        self.bot = bot
        self.data = data
        self.add_item(SaisonSelect(self))

class SaisonSelect(Select):
    def __init__(self, parent_view: SaisonSelectView):
        self.parent_view = parent_view
        options = [discord.SelectOption(label=saison, value=saison) for saison in self.parent_view.data.keys()]
        super().__init__(placeholder="Choisis une saison", options=options)

    async def callback(self, interaction: discord.Interaction):
        saison = self.values[0]
        classement = self.parent_view.data[saison]["Classement"]

        embed = discord.Embed(title=f"🏆 Classement des joueurs — {saison}", color=discord.Color.gold())

        for joueur in classement:
            rang = joueur.get("Rang", "?")
            pseudo = joueur.get("Joueur", "Inconnu")
            persos = joueur.get("Personnages", "—")
            positions = joueur.get("Positions", "—")

            embed.add_field(
                name=f"#{rang}. {pseudo}",
                value=f"🔸 **Persos** : {persos}\n📊 **Positions** : {positions}",
                inline=False
            )

        await safe_edit(
            interaction.message,
            content=None,
            embed=embed,
            view=None
        )

# 🧠 Cog principal
class Classement(commands.Cog):
    """
    Commande !classement — Affiche le classement des joueurs par saison
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="classement",
        help="Affiche le classement des joueurs par saison.",
        description="Affiche les classements séparés par saison avec menu interactif."
    )
    async def classement(self, ctx: commands.Context):
        try:
            data = load_data()
            view = SaisonSelectView(self.bot, data)
            await safe_send(ctx.channel, "📅 Choisis une saison pour voir le classement :", view=view)
        except Exception as e:
            print(f"[ERREUR !classement] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors du chargement du classement.")

# 🔌 Setup du Cog
async def setup(bot: commands.Bot):
    cog = Classement(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Yu-Gi-Oh"
    await bot
.add_cog(cog)
