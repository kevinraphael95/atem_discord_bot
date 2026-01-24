# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygotuto.py
# Objectif : Tutoriel interactif pour apprendre à jouer au Yu-Gi-Oh! TCG
# Catégorie : 🃏 Yu-Gi-Oh!
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
YGO_TUTORIAL_DATA = [
    {
        "titre": "Introduction",
        "contenu": [
            "Yu-Gi-Oh! TCG est un jeu de cartes stratégique basé sur l'univers Yu-Gi-Oh!.",
            "Objectif : réduire les Life Points de ton adversaire à 0 en utilisant des monstres, magies et pièges."
        ]
    },
    {
        "titre": "Types de cartes",
        "contenu": [
            "🟢 Monstres — attaquent et défendent",
            "🔵 Magies — effets instantanés ou permanents",
            "🔴 Pièges — activation réactive aux actions adverses"
        ]
    },
    {
        "titre": "Phases du tour",
        "contenu": [
            "1️⃣ Draw Phase : Pioche une carte",
            "2️⃣ Standby Phase : Effets automatiques",
            "3️⃣ Main Phase 1 : Poser monstres, magies/pièges",
            "4️⃣ Battle Phase : Attaquer avec les monstres",
            "5️⃣ Main Phase 2 : Actions supplémentaires",
            "6️⃣ End Phase : Terminer le tour"
        ]
    },
    {
        "titre": "Combat",
        "contenu": [
            "⚔️ Déclaration des attaques",
            "🛡️ Comparaison des ATK/DEF des monstres",
            "💥 Résolution des dégâts et destruction des cartes",
            "⚠️ Effets de cartes peuvent modifier le combat"
        ]
    },
    {
        "titre": "Gagner la partie",
        "contenu": [
            "❤️ Réduire les Life Points de l'adversaire à 0",
            "📜 Autres conditions spéciales selon les cartes"
        ]
    },
    {
        "titre": "Règles avancées",
        "contenu": [
            "🔹 Invocation spéciale : Synchro, Fusion, XYZ, Lien",
            "🔹 Chaînes : Activation multiple de cartes",
            "🔹 Priorité des effets : Effets rapides vs lents"
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

    async def interaction_check(self, interaction: discord.Interaction):
        return True

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await safe_edit(self.message, embed=self.embed_list[self.index], view=self)
            self.update_buttons()

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.embed_list) - 1:
            self.index += 1
            await safe_edit(self.message, embed=self.embed_list[self.index], view=self)
            self.update_buttons()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec cooldowns centralisés
# ────────────────────────────────────────────────────────────────────────────────
class YGOTuto(commands.Cog):
    """
    Commande /ygotuto et !ygotuto — Tutoriel Yu-Gi-Oh! TCG
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour créer les embeds
    # ────────────────────────────────────────────────────────────────────────────
    def generate_embeds(self):
        embeds = []
        for page in YGO_TUTORIAL_DATA:
            embed = discord.Embed(title=page["titre"], color=discord.Color.purple())
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
        name="ygotuto",
        description="Tutoriel interactif pour apprendre à jouer au Yu-Gi-Oh! TCG"
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_ygotuto(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_tuto(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygotuto")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_ygotuto(self, ctx: commands.Context):
        await self._send_tuto(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOTuto(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
