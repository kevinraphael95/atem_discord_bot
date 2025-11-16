# ────────────────────────────────────────────────────────────────────────────────
# 🎴 deck.py — Commande interactive !deck
# Objectif : Choisir une saison, un duelliste et un genre de deck
# Catégorie : 🧠 VAACT
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import json
import os

from utils.discord_utils import safe_send
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement JSON
# ────────────────────────────────────────────────────────────────────────────────
DECK_JSON_PATH = os.path.join("data", "deck_data.json")

def load_data():
    with open(DECK_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fonction utilitaire pour remplacer un Select dans la View
# ────────────────────────────────────────────────────────────────────────────────
def refresh_select(view, old_select, new_select):
    if old_select in view.children:
        view.remove_item(old_select)
    view.add_item(new_select)

# ────────────────────────────────────────────────────────────────────────────────
# 🏆 Bouton Deck Favori
# ────────────────────────────────────────────────────────────────────────────────
class DeckFavoriteButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="Deck favori", style=discord.ButtonStyle.success, emoji="🏆")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.user or interaction.user.id != self.parent_view.user.id:
            return await interaction.response.send_message("❌ Ce bouton n’est pas pour toi.", ephemeral=True)

        duelliste = self.parent_view.duelliste
        genre = self.parent_view.genre

        if not duelliste or not genre:
            return await interaction.response.send_message("❌ Sélectionne d’abord un deck.", ephemeral=True)

        fav_name = f"{duelliste} — {genre}"

        try:
            supabase.table("profil").upsert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "fav_decks_vaact": fav_name
            }, on_conflict="user_id").execute()

            await interaction.response.send_message(f"✅ **{fav_name}** est maintenant ton deck favori !", ephemeral=True)

        except Exception as e:
            print(f"[ERREUR Supabase] {e}")
            await interaction.response.send_message(
                "❌ Erreur lors de l’ajout du deck favori dans Supabase.",
                ephemeral=True
            )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Select Saison
# ────────────────────────────────────────────────────────────────────────────────
class SaisonSelect(Select):
    def __init__(self, parent_view):
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
        self.parent_view.genre = None

        # --- Nouveau DuellisteSelect ---
        new_duelliste_select = DuellisteSelect(self.parent_view)
        refresh_select(self.parent_view, getattr(self.parent_view, "duelliste_select", None), new_duelliste_select)
        self.parent_view.duelliste_select = new_duelliste_select

        # --- Nouveau GenreSelect désactivé ---
        new_genre_select = GenreSelect(self.parent_view)
        refresh_select(self.parent_view, getattr(self.parent_view, "genre_select", None), new_genre_select)
        self.parent_view.genre_select = new_genre_select

        await interaction.response.edit_message(
            content=f"🎴 Saison sélectionnée : **{chosen}**",
            embed=None,
            view=self.parent_view
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Select Duelliste
# ────────────────────────────────────────────────────────────────────────────────
class DuellisteSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        duels = list(parent_view.deck_data[parent_view.saison].keys())
        options = [discord.SelectOption(label=d, value=d) for d in duels]
        super().__init__(placeholder="👤 Choisis un duelliste", options=options)

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self.parent_view.duelliste = chosen
        self.parent_view.genre = None

        saison = self.parent_view.saison
        deck_info = self.parent_view.deck_data[saison][chosen]["deck"]
        genres = list(deck_info.keys())

        # --- Nouveau GenreSelect avec les options correctes ---
        new_genre_select = GenreSelect(self.parent_view)
        new_genre_select.options = [discord.SelectOption(label=g, value=g) for g in genres]
        new_genre_select.disabled = False

        refresh_select(self.parent_view, getattr(self.parent_view, "genre_select", None), new_genre_select)
        self.parent_view.genre_select = new_genre_select

        await interaction.response.edit_message(
            content=f"👤 Duelliste sélectionné : **{chosen}**\nChoisis maintenant un genre.",
            embed=None,
            view=self.parent_view
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Select Genre
# ────────────────────────────────────────────────────────────────────────────────
class GenreSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        super().__init__(placeholder="🎚️ Choisis un genre", options=[], disabled=True)

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self.parent_view.genre = chosen

        saison = self.parent_view.saison
        duelliste = self.parent_view.duelliste
        deck_info = self.parent_view.deck_data[saison][duelliste]["deck"]

        value = deck_info[chosen]

        # plusieurs sous-parties (Main/Side / Extra…)
        if isinstance(value, dict):
            deck_text = "\n".join(f"• **{k}** : {v}" for k, v in value.items())
        else:
            deck_text = f"• {value}"

        embed = discord.Embed(
            title=f"🧙‍♂️ Deck de {duelliste} — {chosen}",
            description=deck_text,
            color=discord.Color.blue()
        )

        await interaction.response.edit_message(
            content=f"🎴 {saison} → {duelliste} → **{chosen}**",
            embed=embed,
            view=self.parent_view
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 View principale
# ────────────────────────────────────────────────────────────────────────────────
class DeckSelectView(View):
    def __init__(self, bot, deck_data, saison=None, duelliste=None, user=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.deck_data = deck_data
        self.saison = saison or list(deck_data.keys())[0]
        self.duelliste = duelliste
        self.genre = None
        self.user = user

        self.saison_select = SaisonSelect(self)
        self.duelliste_select = DuellisteSelect(self)
        self.genre_select = GenreSelect(self)

        self.add_item(self.saison_select)
        self.add_item(self.duelliste_select)
        self.add_item(self.genre_select)
        self.add_item(DeckFavoriteButton(self))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Commande principale
# ────────────────────────────────────────────────────────────────────────────────
class Deck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="deck",
        help="Affiche les decks du tournoi VAACT.",
        description="Interface interactive : saison, duelliste et genre."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def deck(self, ctx):
        try:
            deck_data = load_data()
            view = DeckSelectView(self.bot, deck_data, user=ctx.author)
            await safe_send(ctx, "📦 Choisis une saison :", view=view)
        except Exception as e:
            print("[ERREUR DECK]", e)
            await safe_send(ctx, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot):
    cog = Deck(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
