# ────────────────────────────────────────────────────────────────────────────────
# 📌 optuto.py
# Objectif : Tutoriel interactif pour apprendre à jouer au One Piece TCG
# Catégorie : OnePieceTCG
# Accès : Tous
# Cooldown : 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_delete  

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON (pages du tutoriel)
# ────────────────────────────────────────────────────────────────────────────────
OPT_TUTORIAL_DATA = [
    {
        "titre": "Introduction",
        "contenu": [
            "One Piece TCG est un jeu de cartes basé sur l'univers de One Piece.",
            "Objectif : réduire les points de vie de l'adversaire ou remplir les conditions spéciales des cartes."
        ]
    },
    {
        "titre": "Types de cartes",
        "contenu": [
            "⚔️ Personnages — combat et capacités",
            "🛠️ Équipements — améliore les personnages",
            "✨ Actions — effets instantanés",
            "🏰 Lieux — avantages permanents"
        ]
    },
    {
        "titre": "Ressources & énergie",
        "contenu": [
            "Chaque carte coûte de l'énergie pour être jouée.",
            "💠 Collecte d'énergie : défausse, actions ou lieux spécifiques.",
            "🔹 Gérer son énergie est crucial pour le timing des actions."
        ]
    },
    {
        "titre": "Déroulement d’un tour",
        "contenu": [
            "1️⃣ Pioche",
            "2️⃣ Phase principale : poser personnages, équipements et lieux",
            "3️⃣ Phase combat : attaquer avec les personnages",
            "4️⃣ Fin de tour"
        ]
    },
    {
        "titre": "Combat",
        "contenu": [
            "🗡️ Déclaration des attaquants",
            "🛡️ Déclaration des défenseurs",
            "💥 Résolution des dégâts et effets",
            "⚠️ Les effets des cartes peuvent changer les règles du combat."
        ]
    },
    {
        "titre": "Gagner la partie",
        "contenu": [
            "❤️ Réduire les points de vie de l'adversaire à 0",
            "📜 Compléter une condition spéciale sur tes cartes"
        ]
    }
]

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue paginée “Suivant / Précédent”
# ────────────────────────────────────────────────────────────────────────────────
class TutoView(View):
    def __init__(self, embed_list, message=None):
        super().__init__(timeout=300)
        self.embed_list = embed_list
        self.message = message
        self.index = 0
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(Button(label="⬅️ Précédent", style=discord.ButtonStyle.blurple, custom_id="prev", disabled=self.index == 0))
        self.add_item(Button(label="➡️ Suivant", style=discord.ButtonStyle.blurple, custom_id="next", disabled=self.index == len(self.embed_list)-1))

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            self.update_buttons()
            await safe_edit(self.message, embed=self.embed_list[self.index], view=self)

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.embed_list) - 1:
            self.index += 1
            self.update_buttons()
            await safe_edit(self.message, embed=self.embed_list[self.index], view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec cooldowns centralisés
# ────────────────────────────────────────────────────────────────────────────────
class OPTTuto(commands.Cog):
    """
    Commande /optuto et !optuto — Tutoriel One Piece TCG
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour créer les embeds
    # ────────────────────────────────────────────────────────────────────────────
    def generate_embeds(self):
        embeds = []
        for page in OPT_TUTORIAL_DATA:
            embed = discord.Embed(title=page["titre"], color=discord.Color.orange())
            embed.description = "\n".join(f"• {line}" for line in page["contenu"])
            embeds.append(embed)
        return embeds

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune pour envoyer le tutoriel
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_tuto(self, channel: discord.abc.Messageable):
        embeds = self.generate_embeds()
        view = TutoView(embeds)
        view.message = await safe_send(channel, embed=embeds[0], view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="optuto",
        description="Tutoriel interactif pour apprendre à jouer au One Piece TCG"
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_optuto(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_tuto(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="optuto", help="Tutoriel interactif pour apprendre à jouer au One Piece TCG")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_optuto(self, ctx: commands.Context):
        await self._send_tuto(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = OPTTuto(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "OnePieceTCG"
    await bot.add_cog(cog)
