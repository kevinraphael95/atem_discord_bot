# ────────────────────────────────────────────────────────────────────────────────
# 📌 bannisougarde.py
# Objectif : Mini-jeu fun Yu-Gi-Oh! où tu décides pour 3 cartes si elles sont bannies,
# gardées à 3 ou limitées à 1.
# Catégorie : 🃏 Minijeux
# Accès : Public
# Cooldown : 1 utilisation / 30 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import random
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Boutons pour chaque carte
# ────────────────────────────────────────────────────────────────────────────────
class ChoixCarteView(View):
    def __init__(self, bot, ctx, cartes, index=0, choix_faits=None, choix_restants=None):
        super().__init__(timeout=120)
        self.bot = bot
        self.ctx = ctx
        self.cartes = cartes
        self.index = index
        self.choix_faits = choix_faits or {}
        self.choix_restants = choix_restants or {"bannir", "garde", "limite"}
        self._init_buttons()

    def _init_buttons(self):
        self.clear_items()
        emoji_map = {"bannir": "🗑️", "garde": "🔥", "limite": "👎"}
        label_map = {"bannir": "Bannir à vie", "garde": "Garder à 3", "limite": "Limiter à 1"}
        for choix in ["bannir", "garde", "limite"]:
            if choix in self.choix_restants:
                self.add_item(ChoixButton(self, choix, label_map[choix], emoji_map[choix]))

    async def update_message(self, interaction):
        carte = self.cartes[self.index]
        embed = discord.Embed(
            title=f"Carte {self.index + 1} / 3 : {carte['name']}",
            description=carte["desc"][:1000],
            color=discord.Color.blue()
        )
        if carte.get("image"):
            embed.set_image(url=carte["image"])
        await safe_edit(interaction.message, content="Choisis le statut de cette carte :", embed=embed, view=self)

    async def avance(self, interaction, choix):
        self.choix_faits[self.index] = choix
        self.choix_restants.remove(choix)
        self.index += 1
        if self.index == len(self.cartes):
            await self.fin(interaction)
            self.stop()
        else:
            self._init_buttons()
            await self.update_message(interaction)

    async def fin(self, interaction):
        embed = discord.Embed(
            title="Résultat du mini-jeu Bannis ou Garde",
            color=discord.Color.green()
        )
        status_map = {"bannir": "🗑️ Bannie à vie", "garde": "🔥 Gardée à 3", "limite": "👎 Limitée à 1"}
        for i, carte in enumerate(self.cartes):
            statut = status_map.get(self.choix_faits.get(i, "?"), "?")
            embed.add_field(name=carte["name"], value=f"{statut}\n{carte['desc'][:300]}...", inline=False)
        await safe_edit(interaction.message, content=None, embed=embed, view=None)
        await safe_send(self.ctx.channel, "Merci d’avoir joué à !bannisougarde 🎲")

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if hasattr(self, "ctx"):
            await safe_send(self.ctx.channel, "⏱️ Temps écoulé, le mini-jeu est terminé.")

class ChoixButton(Button):
    def __init__(self, parent_view: ChoixCarteView, choix: str, label: str, emoji: str):
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
        self.choix = choix

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.ctx.author:
            await interaction.response.send_message("⛔ Ce n'est pas à toi de jouer !", ephemeral=True)
            return
        await interaction.response.defer()
        await self.parent_view.avance(interaction, self.choix)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class BannisOuGarde(commands.Cog):
    """
    Commande /bannisougarde et !bannisougarde — Mini-jeu fun : pour 3 cartes,
    choisis bannir, garder ou limiter.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_random_cards(self):
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                all_cards = data.get("data", [])
                if len(all_cards) < 3:
                    return None
                sample = random.sample(all_cards, 3)
                return [
                    {
                        "name": c["name"],
                        "desc": c["desc"],
                        "image": c.get("card_images", [{}])[0].get("image_url")
                    }
                    for c in sample
                ]

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_game(self, channel: discord.abc.Messageable, author, cartes):
        view = ChoixCarteView(self.bot, author, cartes)
        premiere_carte = cartes[0]
        embed = discord.Embed(
            title=f"Carte 1 / 3 : {premiere_carte['name']}",
            description=premiere_carte['desc'][:1000],
            color=discord.Color.blue()
        )
        if premiere_carte.get("image"):
            embed.set_image(url=premiere_carte["image"])
        embed.set_footer(text="Choisis le statut de cette carte : 🗑️ Bannir, 🔥 Garder, 👎 Limiter")
        await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="bannisougarde",
        description="Mini-jeu : pour 3 cartes, choisis bannir, garder ou limiter."
    )
    @app_commands.checks.cooldown(rate=1, per=30.0, key=lambda i: i.user.id)
    async def slash_bannisougarde(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            cartes = await self.get_random_cards()
            if not cartes:
                return await safe_respond(interaction, "❌ Impossible de récupérer les cartes, réessaie plus tard.", ephemeral=True)
            await self._start_game(interaction.channel, interaction.user, cartes)
            await interaction.delete_original_response()
        except Exception as e:
            print(f"[ERREUR /bannisougarde] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="bannisougarde", aliases=["bog"], help="Mini-jeu : pour 3 cartes, choisis bannir, garder ou limiter.")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def prefix_bannisougarde(self, ctx: commands.Context):
        try:
            cartes = await self.get_random_cards()
            if not cartes:
                return await safe_send(ctx.channel, "❌ Impossible de récupérer les cartes, réessaie plus tard.")
            await self._start_game(ctx.channel, ctx, cartes)
        except Exception as e:
            print(f"[ERREUR !bannisougarde] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = BannisOuGarde(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
