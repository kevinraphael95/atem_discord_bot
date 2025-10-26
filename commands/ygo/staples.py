# ────────────────────────────────────────────────────────────────────────────────
# 📌 staples.py — Commande interactive /staples et !staples
# Objectif :
#   - Récupère les cartes Staples depuis l’API YGOPRODeck
#   - Affiche les résultats avec pagination (20 cartes/page)
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination des staples
# ────────────────────────────────────────────────────────────────────────────────
class StaplesPagination(discord.ui.View):
    def __init__(self, staples: list[dict], per_page: int = 20):
        super().__init__(timeout=180)
        self.staples = staples
        self.per_page = per_page
        self.page = 0

    def get_page_data(self):
        """Retourne les cartes pour la page actuelle."""
        start = self.page * self.per_page
        end = start + self.per_page
        return self.staples[start:end]

    async def update_embed(self, interaction: discord.Interaction):
        """Met à jour l'embed affiché."""
        current = self.get_page_data()
        total_pages = (len(self.staples) - 1) // self.per_page + 1

        embed = discord.Embed(
            title=f"📌 Cartes Staples (Page {self.page + 1}/{total_pages})",
            description="\n".join(f"**{c['name']}** — {c['type']}" for c in current),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{len(self.staples)} cartes au total • 20 par page")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % ((len(self.staples) - 1) // self.per_page + 1)
        await self.update_embed(interaction)

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % ((len(self.staples) - 1) // self.per_page + 1)
        await self.update_embed(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Staples(commands.Cog):
    """Commande /staples et !staples — Liste des cartes Staples"""

    API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_staples(self):
        """Récupère les cartes staples depuis l'API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("data", [])

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="staples",
        description="Affiche une liste de cartes considérées comme staples (20 par page)."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_staples(self, interaction: discord.Interaction):
        await safe_respond(interaction, "🔄 Récupération des cartes staples…")
        staples = await self.fetch_staples()
        if not staples:
            return await safe_respond(interaction, "❌ Impossible de récupérer les cartes staples.")

        view = StaplesPagination(staples)
        current = view.get_page_data()
        total_pages = (len(staples) - 1) // view.per_page + 1

        embed = discord.Embed(
            title=f"📌 Cartes Staples (Page 1/{total_pages})",
            description="\n".join(f"**{c['name']}** — {c['type']}" for c in current),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{len(staples)} cartes au total • 20 par page")
        await interaction.edit_original_response(embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="staples")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_staples(self, ctx: commands.Context):
        msg = await safe_send(ctx.channel, "🔄 Récupération des cartes staples…")
        staples = await self.fetch_staples()
        if not staples:
            return await safe_send(ctx.channel, "❌ Impossible de récupérer les cartes staples.")

        view = StaplesPagination(staples)
        current = view.get_page_data()
        total_pages = (len(staples) - 1) // view.per_page + 1

        embed = discord.Embed(
            title=f"📌 Cartes Staples (Page 1/{total_pages})",
            description="\n".join(f"**{c['name']}** — {c['type']}" for c in current),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{len(staples)} cartes au total • 20 par page")
        await msg.edit(content=None, embed=embed, view=view)

    def cog_load(self):
        self.staples.category = "🃏 Yu-Gi-Oh!"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Staples(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
