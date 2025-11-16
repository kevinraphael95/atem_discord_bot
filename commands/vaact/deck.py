# ────────────────────────────────────────────────────────────────────────────────
# 🎴 deck.py — Commande interactive !deck
# Objectif : Choisir une saison, un duelliste et la version du deck pour afficher son deck et ses astuces
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
            try:
                await interaction.response.send_message("❌ Ce bouton n’est pas pour toi.", ephemeral=True)
            except Exception:
                pass
            return

        duelliste = self.parent_view.duelliste
        deck_version = getattr(self.parent_view, "deck_version", None)
        if not duelliste or not deck_version:
            try:
                await interaction.response.send_message("❌ Aucun deck sélectionné.", ephemeral=True)
            except Exception:
                pass
            return

        try:
            supabase.table("profil").upsert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "fav_decks_vaact": f"{duelliste} ({deck_version})"
            }, on_conflict="user_id").execute()

            try:
                await interaction.response.send_message(
                    f"✅ **{duelliste} ({deck_version})** est maintenant ton deck favori !",
                    ephemeral=True
                )
            except Exception:
                pass
        except Exception as e:
            print(f"[ERREUR Supabase] {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erreur lors de l’ajout du deck favori dans Supabase.",
                    ephemeral=True
                )
            except Exception:
                pass

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Sélection dynamique
# ────────────────────────────────────────────────────────────────────────────────
class DeckSelectView(View):
    def __init__(self, bot, deck_data, saison=None, duelliste=None, user=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.deck_data = deck_data
        self.saison = saison or list(deck_data.keys())[0]
        self.duelliste = duelliste
        self.deck_version = None
        self.user = user
        self.message = None

        # Ajout des selects et du bouton
        self.saison_select = SaisonSelect(self)
        self.duelliste_select = DuellisteSelect(self)
        self.deck_version_select = DeckVersionSelect(self)

        self.add_item(self.saison_select)
        self.add_item(self.duelliste_select)
        self.add_item(self.deck_version_select)
        self.add_item(DeckFavoriteButton(self))

    async def update_embed(self):
        """Met à jour l'embed selon saison, duelliste et version sélectionnées"""
        saison = self.saison
        duelliste = self.duelliste
        version = self.deck_version

        title = "🧙‍♂️ Sélection du deck"
        embed = discord.Embed(title=title, color=discord.Color.blue())

        if duelliste:
            if version:
                deck_data = self.deck_data[saison][duelliste]["deck"][version]
                deck_text = "\n".join(f"• {c}" for c in deck_data) if isinstance(deck_data, list) else deck_data
                embed.title = f"🧙‍♂️ Deck de {duelliste} ({version}) - Saison {saison}"
                embed.add_field(name="📘 Deck", value=deck_text, inline=False)
            astuces_data = self.deck_data[saison][duelliste].get("astuces", "❌ Aucune astuce disponible.")
            astuces_text = "\n".join(f"• {a}" for a in astuces_data) if isinstance(astuces_data, list) else astuces_data
            embed.add_field(name="💡 Astuces", value=astuces_text, inline=False)
        else:
            embed.description = "Sélectionne un duelliste et une version pour voir le deck."

        content = f"🎴 Saison choisie : **{saison}**\nSélectionne un duelliste et une version :"
        if self.message:
            try:
                await self.message.edit(content=content, embed=embed, view=self)
            except Exception:
                try:
                    await self.message.channel.send(content=content, embed=embed)
                except Exception:
                    pass

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Selects
# ────────────────────────────────────────────────────────────────────────────────
class SaisonSelect(Select):
    def __init__(self, parent_view: DeckSelectView):
        self.parent_view = parent_view
        options = [discord.SelectOption(label=s, value=s, default=(s == self.parent_view.saison))
                   for s in self.parent_view.deck_data]
        super().__init__(placeholder="📅 Choisis une saison du tournoi VAACT", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.saison = self.values[0]
        # Mise à jour des duellistes et versions
        duellistes = list(self.parent_view.deck_data[self.parent_view.saison].keys())
        self.parent_view.duelliste_select.options = [discord.SelectOption(label=d, value=d) for d in duellistes]
        self.parent_view.duelliste = None
        self.parent_view.deck_version_select.update_options()
        self.parent_view.deck_version = None
        await self.parent_view.update_embed()

class DuellisteSelect(Select):
    def __init__(self, parent_view: DeckSelectView):
        self.parent_view = parent_view
        duellistes = list(self.parent_view.deck_data[self.parent_view.saison].keys())
        options = [discord.SelectOption(label=d, value=d, default=(d == self.parent_view.duelliste))
                   for d in duellistes]
        super().__init__(placeholder="👤 Choisis un duelliste", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.duelliste = self.values[0]
        # Mise à jour DeckVersionSelect
        self.parent_view.deck_version_select.update_options()
        self.parent_view.deck_version = None
        await self.parent_view.update_embed()

class DeckVersionSelect(Select):
    def __init__(self, parent_view: DeckSelectView):
        self.parent_view = parent_view
        self.options = []
        self.update_options()
        super().__init__(placeholder="📂 Choisis une version du deck", options=self.options)

    def update_options(self):
        self.options = []
        duelliste = self.parent_view.duelliste
        saison = self.parent_view.saison
        if duelliste and saison:
            deck_versions = list(self.parent_view.deck_data[saison][duelliste].get("deck", {}).keys())
            self.options = [discord.SelectOption(label=v, value=v) for v in deck_versions]

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.deck_version = self.values[0]
        await self.parent_view.update_embed()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Deck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="deck",
        help="Affiche les decks du tournoi VAACT, organisés par saison.",
        description="Affiche une interface interactive pour choisir une saison, un duelliste et la version du deck."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def deck(self, ctx: commands.Context):
        try:
            deck_data = load_data()
            view = DeckSelectView(self.bot, deck_data, user=ctx.author)
            msg = await safe_send(ctx, "📦 Choisis une saison :", view=view)
            view.message = msg
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
