# ────────────────────────────────────────────────────────────────────────────────
# 📌 deck.py — Commande interactive !deck et /deck
# Objectif : Choisir une saison + un duelliste et afficher ses decks (sans astuces)
# Catégorie : VAACT
# Accès : Tous
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
import json
import os

from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement du fichier JSON deck_data.json
# ────────────────────────────────────────────────────────────────────────────────
DECK_JSON_PATH = os.path.join("data", "deck_data.json")

def load_data():
    """Charge et renvoie les données du fichier JSON."""
    try:
        with open(DECK_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON deck_data] {e}")
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🏆 Bouton — Sauvegarde du deck favori
# ────────────────────────────────────────────────────────────────────────────────
class DeckFavoriteButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="Deck favori", style=discord.ButtonStyle.success, emoji="🏆")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.user or interaction.user.id != self.parent_view.user.id:
            return await interaction.response.send_message("❌ Ce bouton n’est pas pour toi.", ephemeral=True)

        duelliste = self.parent_view.duelliste
        if not duelliste:
            return await interaction.response.send_message("❌ Aucun deck sélectionné.", ephemeral=True)

        try:
            supabase.table("profil").upsert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "fav_decks_vaact": duelliste
            }, on_conflict="user_id").execute()

            return await interaction.response.send_message(
                f"✅ **{duelliste}** est maintenant ton deck favori !", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR Supabase] {e}")
            return await interaction.response.send_message("❌ Erreur Supabase.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Sélection Saison + Duelliste + Favori
# ────────────────────────────────────────────────────────────────────────────────
class DeckSelectView(View):
    def __init__(self, bot, deck_data, saison=None, duelliste=None, user=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.deck_data = deck_data
        self.saison = saison or list(deck_data.keys())[0]
        self.duelliste = duelliste
        self.user = user

        self.saison_select = SaisonSelect(self)
        self.duelliste_select = DuellisteSelect(self)

        self.add_item(self.saison_select)
        self.add_item(self.duelliste_select)
        self.add_item(DeckFavoriteButton(self))

# ────────────────────────────────────────────────────────────────────────────────
# 📅 Select Saison
# ────────────────────────────────────────────────────────────────────────────────
class SaisonSelect(Select):
    def __init__(self, parent_view: DeckSelectView):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(label=s, value=s, default=(s == parent_view.saison))
            for s in parent_view.deck_data
        ]

        super().__init__(placeholder="📅 Choisis une saison", options=options)

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self.parent_view.saison = chosen
        self.parent_view.duelliste = None

        duellistes = sorted(self.parent_view.deck_data.get(chosen, {}).keys())

        self.parent_view.duelliste_select.options = [
            discord.SelectOption(label=d, value=d)
            for d in duellistes
        ]

        self.options = [
            discord.SelectOption(label=s, value=s, default=(s == chosen))
            for s in self.parent_view.deck_data
        ]

        await interaction.response.edit_message(
            content=f"🎴 Saison choisie : **{chosen}**\nSélectionne un duelliste :",
            embed=None,
            view=self.parent_view
        )

# ────────────────────────────────────────────────────────────────────────────────
# 👤 Select Duelliste
# ────────────────────────────────────────────────────────────────────────────────
class DuellisteSelect(Select):
    def __init__(self, parent_view: DeckSelectView):
        self.parent_view = parent_view

        duellistes = sorted(parent_view.deck_data.get(parent_view.saison, {}).keys())
        options = [
            discord.SelectOption(label=d, value=d, default=(d == parent_view.duelliste))
            for d in duellistes
        ]

        super().__init__(placeholder="👤 Choisis un duelliste", options=options)

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self.parent_view.duelliste = chosen

        saison = self.parent_view.saison
        duellistes = sorted(self.parent_view.deck_data.get(saison, {}).keys())

        self.options = [
            discord.SelectOption(label=d, value=d, default=(d == chosen))
            for d in duellistes
        ]

        infos = self.parent_view.deck_data.get(saison, {}).get(chosen, {})
        deck_data = infos.get("deck", {})

        deck_text = self.format_deck(deck_data)

        embed = discord.Embed(
            title=f"🎴 Deck de {chosen}",
            description=f"Saison :**{saison}**",
            color=discord.Color.gold()
        )

        # embed.set_thumbnail(url="https://i.imgur.com/u7CEp4p.png")
        embed.add_field(name="📘 Deck(s)", value=deck_text, inline=False)

        await interaction.response.edit_message(
            content=f"🎴 Saison choisie : **{saison}**\nSélectionne un duelliste :",
            embed=embed,
            view=self.parent_view
        )

    @staticmethod
    def format_deck(deck_data):
        if isinstance(deck_data, str):
            return deck_data

        if isinstance(deck_data, dict):
            result = []
            for niveau, contenu in deck_data.items():
                result.append(f"**{niveau}** :")
                if isinstance(contenu, str):
                    result.append(f"• {contenu}")
                else:
                    for sous, url in contenu.items():
                        result.append(f"  └─ **{sous}** : {url}")
            return "\n".join(result)

        return "❌ Aucun deck disponible."

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Deck(commands.Cog):
    """
    Commande /deck et !deck — Interface de sélection des decks VAACT
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="deck", description="Choisis une saison et un duelliste pour voir ses decks")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_deck(self, interaction: discord.Interaction):
        deck_data = load_data()
        if not deck_data:
            return await safe_respond(interaction, "❌ Impossible de charger les decks.")

        view = DeckSelectView(self.bot, deck_data, user=interaction.user)
        await interaction.response.send_message("📦 Choisis une saison :", view=view, ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="deck", help="Choisis une saison et un duelliste pour voir ses decks")
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_deck(self, ctx: commands.Context):
        deck_data = load_data()
        if not deck_data:
            return await safe_send(ctx.channel, "❌ Impossible de charger les decks.")

        view = DeckSelectView(self.bot, deck_data, user=ctx.author)
        await safe_send(ctx.channel, "📦 Choisis une saison :", view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Deck(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
