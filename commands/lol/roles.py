# ────────────────────────────────────────────────────────────────────────────────
# 📌 roles.py — Commande interactive !role
# Objectif : Afficher les rôles LoL et leurs descriptions via menu déroulant
# Catégorie : LoL
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Select
import json
import os

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "lol", "roles.json")

def load_data():
    """Charge les données des rôles LoL depuis le fichier JSON."""
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Menu unique de sélection d'un rôle
# ────────────────────────────────────────────────────────────────────────────────
class RoleSelectView(View):
    """Vue avec menu pour choisir un rôle LoL."""
    def __init__(self, bot, roles_data):
        super().__init__(timeout=120)
        self.bot = bot
        self.roles_data = roles_data
        self.add_item(RoleSelect(self))

class RoleSelect(Select):
    """Menu déroulant des rôles LoL."""
    def __init__(self, parent_view: RoleSelectView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=emoji + " " + name, value=name)
            for name, data in self.parent_view.roles_data.items()
            for emoji in [data.get("emoji", "❓")]
        ]
        super().__init__(placeholder="Sélectionne un rôle LoL", options=options)

    async def callback(self, interaction: discord.Interaction):
        role_name = self.values[0]
        role_info = self.parent_view.roles_data[role_name]

        embed = discord.Embed(
            title=f"{role_info.get('emoji', '')} {role_name}",
            description=role_info.get("role", "Rôle inconnu"),
            color=discord.Color.green()
        )

        embed.add_field(name="🎯 Objectif", value=role_info.get("objectif", "Non précisé"), inline=False)
        embed.add_field(name="🛠️ Caractéristiques", value=role_info.get("caractéristiques", "Non précisées"), inline=False)
        embed.add_field(name="📌 Exemples", value=", ".join(role_info.get("exemples", [])), inline=False)
        embed.add_field(name="🧠 Image mentale", value=role_info.get("imagine", "—"), inline=False)

        await interaction.response.edit_message(embed=embed, view=None)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class RoleCommand(commands.Cog):
    """
    Commande !role — Affiche les rôles de League of Legends avec descriptions
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="role",
        help="Affiche les rôles LoL via un menu interactif.",
        description="Affiche les rôles jouables dans LoL et leur description (Tank, Mage, ADC, etc.)."
    )
    async def role(self, ctx: commands.Context):
        """Commande principale avec menu déroulant des rôles."""
        try:
            roles_data = load_data()
            view = RoleSelectView(self.bot, roles_data)
            await ctx.send("🔽 Choisis un rôle dans la liste :", view=view)
        except Exception as e:
            print(f"[ERREUR !role] {e}")
            await ctx.send("❌ Une erreur est survenue lors du chargement des rôles.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RoleCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "LoL"
    await bot.add_cog(cog)
