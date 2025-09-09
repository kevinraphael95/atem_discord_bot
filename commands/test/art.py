# ────────────────────────────────────────────────────────────────────────────────
# 📌 art.py — Commande interactive !art
# Objectif : Afficher l’illustration d’une carte Yu-Gi-Oh! par nom, mot de passe ou Konami ID
# Catégorie : Test
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Select
import aiohttp

from utils.discord_utils import safe_send, safe_edit  

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ API — Fonctions utilitaires pour récupérer les cartes
# ────────────────────────────────────────────────────────────────────────────────
API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

async def fetch_card(query_type: str, query: str):
    """Récupère une carte via YGOPRODeck API."""
    params = {}
    if query_type == "name":
        params = {"name": query, "language": "fr"}
    elif query_type == "password":
        params = {"passcode": query, "language": "fr"}
    elif query_type == "konami_id":
        params = {"id": query, "language": "fr"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data["data"][0] if "data" in data and len(data["data"]) > 0 else None
    except Exception as e:
        print(f"[ERREUR API] {e}")
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Sélecteur d’artworks
# ────────────────────────────────────────────────────────────────────────────────
class ArtSelectView(View):
    def __init__(self, images: list[str]):
        super().__init__(timeout=120)
        self.images = images
        self.message = None
        self.add_item(ArtSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class ArtSelect(Select):
    def __init__(self, parent_view: ArtSelectView):
        self.parent_view = parent_view
        options = [discord.SelectOption(label=f"Illustration {i+1}", value=url) for i, url in enumerate(parent_view.images)]
        super().__init__(placeholder="Choisis une illustration", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_url = self.values[0]
        embed = discord.Embed(title="Illustration de la carte", color=discord.Color.blue())
        embed.set_image(url=selected_url)
        await safe_edit(interaction.message, embed=embed, view=self.parent_view)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ArtCommand(commands.Cog):
    """
    Commande !art — Affiche l’illustration d’une carte Yu-Gi-Oh!
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _show_art(self, channel: discord.abc.Messageable, query_type: str, query: str):
        data = await fetch_card(query_type, query)
        if not data:
            await safe_send(channel, f"❌ Impossible de trouver une carte pour `{query}`.")
            return

        images = [img["image_url"] for img in data.get("card_images", [])]
        if not images:
            await safe_send(channel, f"❌ Aucune illustration trouvée pour `{query}`.")
            return

        embed = discord.Embed(title=f"Illustration de {data.get('name', 'Carte inconnue')}", color=discord.Color.blue())
        embed.set_image(url=images[0])

        if len(images) > 1:
            view = ArtSelectView(images)
            view.message = await safe_send(channel, embed=embed, view=view)
        else:
            await safe_send(channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="art")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_art(self, ctx: commands.Context, query_type: str, *, query: str):
        """
        !art <name|password|konami_id> <valeur>
        """
        try:
            await self._show_art(ctx.channel, query_type, query)
        except Exception as e:
            print(f"[ERREUR !art] {e}")
            await safe_send(ctx.channel, "❌ Erreur lors de la recherche de la carte.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ArtCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
