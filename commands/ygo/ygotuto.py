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
from discord.ui import View, Select

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_delete  

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON (pages du tutoriel)
# ────────────────────────────────────────────────────────────────────────────────
YGO_TUTORIAL_DATA = {
    "Introduction": {
        "Contenu": [
            "Yu-Gi-Oh! TCG est un jeu de cartes stratégique basé sur l'univers Yu-Gi-Oh!.",
            "Objectif : réduire les Life Points de ton adversaire à 0 en utilisant des monstres, magies et pièges."
        ]
    },
    "Types de cartes": {
        "Contenu": [
            "🟢 Monstres — attaquent et défendent",
            "🔵 Magies — effets instantanés ou permanents",
            "🔴 Pièges — activation réactive aux actions adverses"
        ]
    },
    "Phases du tour": {
        "Contenu": [
            "1️⃣ Draw Phase : Pioche une carte",
            "2️⃣ Standby Phase : Effets automatiques",
            "3️⃣ Main Phase 1 : Poser monstres, magies/pièges",
            "4️⃣ Battle Phase : Attaquer avec les monstres",
            "5️⃣ Main Phase 2 : Actions supplémentaires",
            "6️⃣ End Phase : Terminer le tour"
        ]
    },
    "Combat": {
        "Contenu": [
            "⚔️ Déclaration des attaques",
            "🛡️ Comparaison des ATK/DEF des monstres",
            "💥 Résolution des dégâts et destruction des cartes",
            "⚠️ Effets de cartes peuvent modifier le combat"
        ]
    },
    "Gagner la partie": {
        "Contenu": [
            "❤️ Réduire les Life Points de l'adversaire à 0",
            "📜 Autres conditions spéciales selon les cartes"
        ]
    },
    "Règles avancées": {
        "Contenu": [
            "🔹 Invocation spéciale : Synchro, Fusion, XYZ, Lien",
            "🔹 Chaînes : Activation multiple de cartes",
            "🔹 Priorité des effets : Effets rapides vs lents"
        ]
    }
}

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Premier menu interactif
# ────────────────────────────────────────────────────────────────────────────────
class FirstSelectView(View):
    def __init__(self, bot, data):
        super().__init__(timeout=300)
        self.bot = bot
        self.data = data
        self.message = None
        self.add_item(FirstSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class FirstSelect(Select):
    def __init__(self, parent_view: FirstSelectView):
        self.parent_view = parent_view
        options = [discord.SelectOption(label=key, value=key) for key in self.parent_view.data.keys()]
        super().__init__(placeholder="Sélectionne une section du tutoriel", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_key = self.values[0]
        new_view = SecondSelectView(self.parent_view.bot, self.parent_view.data, selected_key)
        new_view.message = interaction.message
        await safe_edit(
            interaction.message,
            content=f"Section sélectionnée : **{selected_key}**\nVoici les détails :",
            embed=None,
            view=new_view
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Deuxième menu interactif
# ────────────────────────────────────────────────────────────────────────────────
class SecondSelectView(View):
    def __init__(self, bot, data, key):
        super().__init__(timeout=300)
        self.bot = bot
        self.data = data
        self.key = key
        self.message = None
        self.add_item(SecondSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class SecondSelect(Select):
    def __init__(self, parent_view: SecondSelectView):
        self.parent_view = parent_view
        sub_options = list(self.parent_view.data[self.parent_view.key].keys())
        options = [discord.SelectOption(label=sub, value=sub) for sub in sub_options]
        super().__init__(placeholder="Sélectionne un détail", options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.parent_view.key
        sub_key = self.values[0]
        infos = self.parent_view.data[key][sub_key]

        embed = discord.Embed(
            title=f"{sub_key} — {key}",
            color=discord.Color.purple()
        )
        for field_name, field_value in infos.items():
            value = "\n".join(f"• {item}" for item in field_value) if isinstance(field_value, list) else str(field_value)
            embed.add_field(name=field_name.capitalize(), value=value, inline=False)

        await safe_edit(
            interaction.message,
            content=None,
            embed=embed,
            view=None
        )

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
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_menu(self, channel: discord.abc.Messageable):
        data = YGO_TUTORIAL_DATA
        if not data:
            await safe_send(channel, "❌ Impossible de charger les données.")
            return
        view = FirstSelectView(self.bot, data)
        view.message = await safe_send(channel, "Choisis une section :", view=view)

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
        await self._send_menu(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygotuto")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_ygotuto(self, ctx: commands.Context):
        await self._send_menu(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOTuto(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
