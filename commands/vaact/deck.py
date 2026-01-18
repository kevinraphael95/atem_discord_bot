# ────────────────────────────────────────────────────────────────────────────────
# 📌 deck.py — Commande interactive !deck et /deck (VERSION BOUTONS)
# Objectif : Choisir saison → duelliste → version du deck + favori précis
# Catégorie : VAACT
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import os

from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement JSON
# ────────────────────────────────────────────────────────────────────────────────
DECK_JSON_PATH = os.path.join("data", "deck_data.json")

def load_data():
    try:
        with open(DECK_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[ERREUR JSON]", e)
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View principale
# ────────────────────────────────────────────────────────────────────────────────
class DeckView(View):
    def __init__(self, deck_data, user):
        super().__init__(timeout=300)
        self.deck_data = deck_data
        self.user = user

        self.saison = None
        self.duelliste = None
        self.version = None

        self.show_saisons()

    # ────────────────────────────────────────────────────────────────────────────
    # 📅 Étape 1 — Saisons
    # ────────────────────────────────────────────────────────────────────────────
    def show_saisons(self):
        self.clear_items()
        for saison in self.deck_data.keys():
            self.add_item(SaisonButton(saison, self))

    # ────────────────────────────────────────────────────────────────────────────
    # 👤 Étape 2 — Duellistes
    # ────────────────────────────────────────────────────────────────────────────
    def show_duellistes(self):
        self.clear_items()
        for duel in self.deck_data[self.saison].keys():
            self.add_item(DuellisteButton(duel, self))
        self.add_item(BackButton("⬅️ Saisons", self.show_saisons))

    # ────────────────────────────────────────────────────────────────────────────
    # 🎴 Étape 3 — Versions
    # ────────────────────────────────────────────────────────────────────────────
    def show_versions(self):
        self.clear_items()
        decks = self.deck_data[self.saison][self.duelliste]["deck"]
        for key, data in decks.items():
            self.add_item(VersionButton(key, data, self))
        self.add_item(BackButton("⬅️ Duellistes", self.show_duellistes))

# ────────────────────────────────────────────────────────────────────────────────
# 🔘 Boutons
# ────────────────────────────────────────────────────────────────────────────────
class SaisonButton(Button):
    def __init__(self, saison, view):
        super().__init__(label=saison, style=discord.ButtonStyle.primary)
        self.saison = saison
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.user:
            return await interaction.response.send_message("❌ Pas pour toi.", ephemeral=True)

        self.view_ref.saison = self.saison
        self.view_ref.show_duellistes()

        await interaction.response.edit_message(
            content=f"📅 **{self.saison}** — Choisis un duelliste",
            view=self.view_ref
        )

class DuellisteButton(Button):
    def __init__(self, duelliste, view):
        super().__init__(label=duelliste, style=discord.ButtonStyle.secondary)
        self.duelliste = duelliste
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.user:
            return await interaction.response.send_message("❌ Pas pour toi.", ephemeral=True)

        self.view_ref.duelliste = self.duelliste
        self.view_ref.show_versions()

        await interaction.response.edit_message(
            content=f"👤 **{self.duelliste}** — Choisis une version",
            view=self.view_ref
        )

class VersionButton(Button):
    def __init__(self, key, data, view):
        super().__init__(
            label=data.get("label", key),
            style=discord.ButtonStyle.success
        )
        self.key = key
        self.data = data
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.user:
            return await interaction.response.send_message("❌ Pas pour toi.", ephemeral=True)

        self.view_ref.version = self.key

        embed = discord.Embed(
            title=f"🎴 Deck {self.view_ref.duelliste}",
            description=(
                f"**Saison :** {self.view_ref.saison}\n"
                f"**Version :** {self.data.get('label')}\n"
                f"**Difficulté :** {self.data.get('difficulty')}\n\n"
                f"{self.data.get('description')}\n\n"
                f"🔗 {self.data.get('url')}"
            ),
            color=discord.Color.gold()
        )

        fav_button = FavoriteButton(self.view_ref)
        self.view_ref.add_item(fav_button)

        await interaction.response.edit_message(
            content="",
            embed=embed,
            view=self.view_ref
        )

class FavoriteButton(Button):
    def __init__(self, view):
        super().__init__(label="Favori", emoji="⭐", style=discord.ButtonStyle.success)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        try:
            supabase.table("profil").upsert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "fav_decks_vaact": {
                    "saison": self.view_ref.saison,
                    "duelliste": self.view_ref.duelliste,
                    "version": self.view_ref.version
                }
            }, on_conflict="user_id").execute()

            await interaction.response.send_message(
                "⭐ Deck favori enregistré !",
                ephemeral=True
            )
        except Exception as e:
            print("[ERREUR SUPABASE]", e)
            await interaction.response.send_message("❌ Erreur.", ephemeral=True)

class BackButton(Button):
    def __init__(self, label, action):
        super().__init__(label=label, style=discord.ButtonStyle.danger)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        self.action()
        await interaction.response.edit_message(view=self.view)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog
# ────────────────────────────────────────────────────────────────────────────────
class Deck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="deck", description="Afficher les decks VAACT")
    async def slash_deck(self, interaction: discord.Interaction):
        data = load_data()
        view = DeckView(data, interaction.user)
        await interaction.response.send_message(
            "📅 Choisis une saison",
            view=view,
            ephemeral=True
        )

    @commands.command(name="deck")
    async def prefix_deck(self, ctx):
        data = load_data()
        view = DeckView(data, ctx.author)
        await safe_send(ctx.channel, "📅 Choisis une saison", view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Deck(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
