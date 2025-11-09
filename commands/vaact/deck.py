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
        self.parent_view = parent_view  # on conserve la View pour lire la sélection

    async def callback(self, interaction: discord.Interaction):
        # Restreint au propriétaire
        if not self.parent_view.user or interaction.user.id != self.parent_view.user.id:
            try:
                await interaction.response.send_message("❌ Ce bouton n’est pas pour toi.", ephemeral=True)
            except Exception:
                pass
            return

        duelliste = self.parent_view.duelliste
        if not duelliste:
            try:
                await interaction.response.send_message("❌ Aucun deck sélectionné.", ephemeral=True)
            except Exception:
                pass
            return

        try:
            supabase.table("profil").upsert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.name,
                "fav_decks_vaact": duelliste
            }, on_conflict="user_id").execute()

            try:
                await interaction.response.send_message(
                    f"✅ **{duelliste}** est maintenant ton deck favori !",
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
# 🎛️ UI — Sélection de saison et duelliste
# ────────────────────────────────────────────────────────────────────────────────
class DeckSelectView(View):
    def __init__(self, bot, deck_data, saison=None, duelliste=None, user=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.deck_data = deck_data
        self.saison = saison or list(deck_data.keys())[0]
        self.duelliste = duelliste
        self.user = user

        # on ajoute les selects et le bouton une seule fois
        self.saison_select = SaisonSelect(self)
        self.duelliste_select = DuellisteSelect(self)
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
        # Met à jour la saison choisie
        chosen = self.values[0]
        self.parent_view.saison = chosen

        # Met à jour dynamiquement les options du DuellisteSelect selon la saison choisie
        duellistes = list(self.parent_view.deck_data.get(chosen, {}).keys())
        new_options = [
            discord.SelectOption(label=d, value=d, default=False)
            for d in duellistes
        ]
        # Remplace les options sans recréer le Select
        try:
            self.parent_view.duelliste_select.options = new_options
            # Reset la sélection courante (on ne sélectionne rien automatiquement)
            self.parent_view.duelliste = None
        except Exception:
            pass

        # Édite le message pour refléter le changement de saison (sans embed)
        content = f"🎴 Saison choisie : **{self.parent_view.saison}**\nSélectionne un duelliste :"
        try:
            await interaction.response.edit_message(content=content, embed=None, view=self.parent_view)
        except Exception:
            # Si edit_message échoue, essaie de répondre proprement (silencieux)
            try:
                await interaction.response.send_message(content, ephemeral=True)
            except Exception:
                pass

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
        # Met à jour le duelliste sélectionné
        chosen = self.values[0]
        self.parent_view.duelliste = chosen
        duelliste = chosen
        saison = self.parent_view.saison

        infos = self.parent_view.deck_data.get(saison, {}).get(duelliste, {})
        deck_data = infos.get("deck", "❌ Aucun deck trouvé.")
        astuces_data = infos.get("astuces", "❌ Aucune astuce disponible.")

        deck_text = "\n".join(f"• {c}" for c in deck_data) if isinstance(deck_data, list) else deck_data
        astuces_text = "\n".join(f"• {a}" for a in astuces_data) if isinstance(astuces_data, list) else astuces_data

        embed = discord.Embed(
            title=f"🧙‍♂️ Deck de {duelliste} (Saison {saison})",
            color=discord.Color.blue()
        )
        embed.add_field(name="📘 Deck(s)", value=deck_text, inline=False)
        embed.add_field(name="💡 Astuces", value=astuces_text, inline=False)

        # On édite le message pour afficher le deck et conserver la même View (avec le bouton qui utilisera self.parent_view.duelliste)
        content = f"🎴 Saison choisie : **{saison}**\nSélectionne un duelliste :"
        try:
            await interaction.response.edit_message(content=content, embed=embed, view=self.parent_view)
        except Exception:
            # fallback silencieux
            try:
                await interaction.response.send_message("❌ Impossible de mettre à jour l'affichage.", ephemeral=True)
            except Exception:
                pass

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
