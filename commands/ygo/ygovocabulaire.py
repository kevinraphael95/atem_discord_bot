# ================================================================================
# 📌 vocabulaire.py — Commande interactive !vocabulaire
# Objectif :
#   - Affiche les définitions des termes du jeu depuis un fichier JSON
#   - Permet la navigation entre pages avec des boutons
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# Cooldown : 1 utilisation / 5 sec / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import os

from utils.discord_utils import safe_send, safe_edit, safe_respond

# ================================================================================
# 📂 Chargement des données JSON
# ================================================================================
VOCAB_PATH = os.path.join("data", "vocabulaire.json")

def load_data():
    try:
        with open(VOCAB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {VOCAB_PATH} : {e}")
        return {}

# ================================================================================
# 🎛️ View — Pagination interactive
# ================================================================================
class VocabulaireView(View):
    def __init__(self, pages: list[discord.Embed]):
        super().__init__(timeout=120)
        self.pages = pages
        self.index = 0
        self.message = None

    async def update(self, interaction: discord.Interaction):
        await safe_edit(self.message, embed=self.pages[self.index], view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.pages)
        await self.update(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(self.pages)
        await self.update(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class VocabulaireCommand(commands.Cog):
    """Commande /vocabulaire et !vocabulaire — Définitions interactives de termes Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _show_vocab(self, channel: discord.abc.Messageable, mot_cle: str = None):
        data = load_data()
        if not data:
            await safe_send(channel, "❌ Impossible de charger le lexique.")
            return

        definitions = []
        for terme, info in data.items():
            definition = info.get("definition") if isinstance(info, dict) else info
            synonymes = info.get("synonymes", []) if isinstance(info, dict) else []
            noms_possibles = [terme] + synonymes

            if mot_cle:
                if any(mot_cle.lower() in mot.lower() for mot in noms_possibles) or (definition and mot_cle.lower() in definition.lower()):
                    definitions.append((terme, definition))
            else:
                definitions.append((terme, definition))

        if not definitions:
            await safe_send(channel, "❌ Aucun terme trouvé correspondant à ta recherche.")
            return

        definitions.sort(key=lambda x: x[0].lower())
        max_par_page = 5
        pages = []
        total_pages = (len(definitions) - 1) // max_par_page + 1

        for i in range(0, len(definitions), max_par_page):
            embed = discord.Embed(title="📘 Lexique des termes", color=discord.Color.dark_blue())
            for terme, defi in definitions[i:i + max_par_page]:
                embed.add_field(name=f"🔹 {terme}", value=defi or "Aucune définition disponible.", inline=False)
            embed.set_footer(text=f"📄 Page {len(pages) + 1}/{total_pages}")
            pages.append(embed)

        view = VocabulaireView(pages)
        view.message = await safe_send(channel, embed=pages[0], view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ygovocabulaire",
        description="Affiche les définitions des termes Yu-Gi-Oh! avec navigation interactive."
    )
    @app_commands.describe(mot_cle="Mot-clé à rechercher (optionnel)")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_vocabulaire(self, interaction: discord.Interaction, mot_cle: str = None):
        await interaction.response.defer()
        await self._show_vocab(interaction.channel, mot_cle)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="ygovocabulaire", aliases=["ygovoc", "yvoc"], help="📘 Affiche les définitions des termes Yu-Gi-Oh! avec navigation interactive.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_vocabulaire(self, ctx: commands.Context, *, mot_cle: str = None):
        await self._show_vocab(ctx.channel, mot_cle)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = VocabulaireCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
