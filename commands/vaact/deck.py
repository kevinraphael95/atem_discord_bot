# ────────────────────────────────────────────────────────────────────────────────
# 🎴 deck.py — Commande interactive !deck
# Objectif : Choisir une saison et un duelliste pour afficher son deck et ses astuces
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
# 📂 Chargement des données JSON — deck_data.json
# ────────────────────────────────────────────────────────────────────────────────
DECK_JSON_PATH = os.path.join("data", "deck_data.json")

def load_data():
    with open(DECK_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — bouton "Deck favori"
# ────────────────────────────────────────────────────────────────────────────────
class DeckFavoriteButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="Deck favori", style=discord.ButtonStyle.success, emoji="🏆")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.user or interaction.user.id != self.parent_view.user.id:
            try: await interaction.response.send_message("❌ Ce bouton n’est pas pour toi.", ephemeral=True)
            except Exception: pass
            return

        duelliste = self.parent_view.duelliste
        version = self.parent_view.chosen_version or "Débutant"
        if not duelliste:
            try: await interaction.response.send_message("❌ Aucun deck sélectionné.", ephemeral=True)
            except Exception: pass
            return

        try:
            supabase.table("profil").upsert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "fav_decks_vaact": f"{duelliste} ({version})"
            }, on_conflict="user_id").execute()

            try:
                await interaction.response.send_message(f"✅ **{duelliste} ({version})** est maintenant ton deck favori !", ephemeral=True)
            except Exception: pass
        except Exception as e:
            print(f"[ERREUR Supabase] {e}")
            try:
                await interaction.response.send_message("❌ Erreur lors de l’ajout du deck favori dans Supabase.", ephemeral=True)
            except Exception: pass

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Sélection de saison, duelliste et version
# ────────────────────────────────────────────────────────────────────────────────
class DeckSelectView(View):
    def __init__(self, bot, deck_data, saison=None, duelliste=None, user=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.deck_data = deck_data
        self.saison = saison or list(deck_data.keys())[0]
        self.duelliste = duelliste
        self.user = user
        self.chosen_version = None

        # Sélecteurs
        self.saison_select = SaisonSelect(self)
        self.duelliste_select = DuellisteSelect(self)
        self.version_select = None  # créé dynamiquement si plusieurs versions

        # Ajout des items : saison -> duelliste -> version (dynamique) -> bouton
        self.add_item(self.saison_select)
        self.add_item(self.duelliste_select)
        self.add_item(DeckFavoriteButton(self))

class SaisonSelect(Select):
    def __init__(self, parent_view: DeckSelectView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=s, value=s, default=(s == self.parent_view.saison))
            for s in self.parent_view.deck_data
        ]
        super().__init__(placeholder="📅 Choisis une saison du tournoi VAACT", options=options)

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self.parent_view.saison = chosen
        duellistes = list(self.parent_view.deck_data.get(chosen, {}).keys())
        self.parent_view.duelliste_select.options = [discord.SelectOption(label=d, value=d) for d in duellistes]
        self.parent_view.duelliste = None

        # Supprime l'ancien menu version
        if self.parent_view.version_select:
            self.parent_view.remove_item(self.parent_view.version_select)
            self.parent_view.version_select = None
            self.parent_view.chosen_version = None

        content = f"🎴 Saison choisie : **{chosen}**\nSélectionne un duelliste :"
        try: await interaction.response.edit_message(content=content, embed=None, view=self.parent_view)
        except Exception:
            try: await interaction.response.send_message(content, ephemeral=True)
            except Exception: pass

class DuellisteSelect(Select):
    def __init__(self, parent_view: DeckSelectView):
        self.parent_view = parent_view
        duellistes = list(self.parent_view.deck_data.get(self.parent_view.saison, {}).keys())
        options = [
            discord.SelectOption(label=d, value=d, default=(d == self.parent_view.duelliste))
            for d in duellistes
        ]
        super().__init__(placeholder="👤 Choisis un deck", options=options)

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self.parent_view.duelliste = chosen
        deck_info = self.parent_view.deck_data.get(self.parent_view.saison, {}).get(chosen, {}).get("deck", {})

        # Gestion menu version si plusieurs
        if isinstance(deck_info, dict):
            versions = list(deck_info.keys())
            default_version = "Version Débutant" if "Version Débutant" in versions else versions[0]
            self.parent_view.chosen_version = default_version

            # Supprime ancien menu version
            if self.parent_view.version_select:
                self.parent_view.remove_item(self.parent_view.version_select)

            # Crée le menu version sous le duelliste
            if len(versions) > 1:
                self.parent_view.version_select = VersionSelect(self.parent_view, versions)
                self.parent_view.add_item(self.parent_view.version_select)
        else:
            self.parent_view.chosen_version = "Deck"

        await self.display_deck(interaction)

    async def display_deck(self, interaction: discord.Interaction):
        duelliste = self.parent_view.duelliste
        saison = self.parent_view.saison
        chosen_version = self.parent_view.chosen_version
        deck_info = self.parent_view.deck_data.get(saison, {}).get(duelliste, {}).get("deck", {})

        # Récupère le deck selon la version choisie
        if isinstance(deck_info, dict):
            version_data = deck_info.get(chosen_version, [])
            deck_text = "\n".join(f"• {d}" for d in version_data) if isinstance(version_data, list) else str(version_data)
        else:
            deck_text = "\n".join(f"• {d}" for d in deck_info) if isinstance(deck_info, list) else str(deck_info)

        embed = discord.Embed(
            title=f"🧙‍♂️ Deck de {duelliste} ({chosen_version})",
            color=discord.Color.blue()
        )
        embed.add_field(name="📘 Deck", value=deck_text, inline=False)

        content = f"🎴 Saison choisie : **{saison}**\nSélectionne un duelliste :"
        try: await interaction.response.edit_message(content=content, embed=embed, view=self.parent_view)
        except Exception:
            try: await interaction.response.send_message("❌ Impossible de mettre à jour l'affichage.", ephemeral=True)
            except Exception: pass

class VersionSelect(Select):
    """Sélecteur de version de deck (Débutant / Expert / Ext. Duel)"""
    def __init__(self, parent_view: DeckSelectView, versions):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=v, value=v, default=(v == self.parent_view.chosen_version))
            for v in versions
        ]
        super().__init__(placeholder="🃏 Choisis une version du deck", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.chosen_version = self.values[0]
        await self.parent_view.duelliste_select.display_deck(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Deck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="deck",
        help="Affiche les decks du tournoi VAACT, organisés par saison.",
        description="Affiche une interface interactive pour choisir une saison et un duelliste."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def deck(self, ctx: commands.Context):
        try:
            deck_data = load_data()
            view = DeckSelectView(self.bot, deck_data, user=ctx.author)
            await safe_send(ctx, "📦 Choisis une saison :", view=view)
        except Exception as e:
            print("[ERREUR DECK]", e)
            await safe_send(ctx, "❌ Une erreur est survenue lors du chargement des decks.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Deck(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
