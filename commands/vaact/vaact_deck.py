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
import os
import json
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button

from utils.vaact_utils import DB_PATH, get_or_create_profile
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement du fichier JSON deck_data.json
# ────────────────────────────────────────────────────────────────────────────────
DECK_JSON_PATH = os.path.join("data", "deck_data.json")


def load_deck_data() -> dict:
    """Charge deck_data.json une seule fois au démarrage. Retourne {} en cas d'erreur."""
    try:
        with open(DECK_JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[deck] Erreur chargement JSON : {e}")
        return {}


def format_deck(deck_data) -> str:
    """
    Formate les données d'un deck pour l'affichage dans un embed Discord.

    Formats supportés :
      - str   → retourné tel quel
      - dict  → formaté avec niveaux et sous-niveaux
      - autre → message d'erreur
    """
    if isinstance(deck_data, str):
        return deck_data

    if isinstance(deck_data, dict):
        lines = []
        for niveau, contenu in deck_data.items():
            lines.append(f"**{niveau}** :")
            if isinstance(contenu, str):
                lines.append(f"• {contenu}")
            elif isinstance(contenu, dict):
                for sous_niveau, url in contenu.items():
                    lines.append(f"  └─ **{sous_niveau}** : {url}")
        return "\n".join(lines) if lines else "Aucun deck renseigné."

    return "❌ Format de deck non reconnu."

# ────────────────────────────────────────────────────────────────────────────────
# 📅 Select Saison
# ────────────────────────────────────────────────────────────────────────────────
class SaisonSelect(Select):
    def __init__(self, parent: "DeckView"):
        self.parent = parent
        options = [
            discord.SelectOption(label=s, value=s, default=(s == parent.saison))
            for s in parent.deck_data
        ]
        super().__init__(placeholder="📅 Choisis une saison", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent.saison = self.values[0]
        self.parent.duelliste = None
        await self.parent.refresh(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 👤 Select Duelliste
# ────────────────────────────────────────────────────────────────────────────────
class DuellisteSelect(Select):
    def __init__(self, parent: "DeckView"):
        self.parent = parent
        options = self._build_options(parent)
        disabled = not options
        placeholder = "👤 Choisis un duelliste" if options else "Aucun duelliste disponible"
        # Discord exige au moins 1 option même si le select est désactivé
        super().__init__(
            placeholder=placeholder,
            options=options or [discord.SelectOption(label="-", value="-")],
            disabled=disabled,
        )

    @staticmethod
    def _build_options(parent: "DeckView") -> list[discord.SelectOption]:
        duellistes = sorted(parent.deck_data.get(parent.saison, {}).keys())
        return [
            discord.SelectOption(label=d, value=d, default=(d == parent.duelliste))
            for d in duellistes
        ]

    async def callback(self, interaction: discord.Interaction):
        self.parent.duelliste = self.values[0]
        await self.parent.refresh(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🏆 Bouton — Sauvegarde du deck favori (SQLite via vaact_utils)
# ────────────────────────────────────────────────────────────────────────────────
class FavoriButton(Button):
    def __init__(self, parent: "DeckView"):
        super().__init__(label="Deck favori", style=discord.ButtonStyle.success, emoji="🏆")
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        # Seul l'auteur de la commande peut utiliser ce bouton
        if interaction.user.id != self.parent.author_id:
            return await interaction.response.send_message(
                "❌ Ce bouton ne t'est pas destiné.", ephemeral=True
            )

        if not self.parent.duelliste:
            return await interaction.response.send_message(
                "❌ Sélectionne d'abord un duelliste.", ephemeral=True
            )

        await get_or_create_profile(interaction.user.id, interaction.user.name)

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE profil SET fav_decks_vaact = ? WHERE user_id = ?",
                    (self.parent.duelliste, str(interaction.user.id)),
                )
            await interaction.response.send_message(
                f"✅ **{self.parent.duelliste}** enregistré comme deck favori !", ephemeral=True
            )
        except sqlite3.Error as e:
            print(f"[deck] Erreur SQLite FavoriButton : {e}")
            await interaction.response.send_message(
                "❌ Impossible d'enregistrer le deck favori.", ephemeral=True
            )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View principale — Gère l'état et orchestre les composants
# ────────────────────────────────────────────────────────────────────────────────
class DeckView(View):
    """
    Vue interactive avec :
      - un sélecteur de saison
      - un sélecteur de duelliste (mis à jour dynamiquement)
      - un bouton pour sauvegarder le deck favori
    """

    def __init__(self, deck_data: dict, author_id: int):
        super().__init__(timeout=300)
        self.deck_data = deck_data
        self.author_id = author_id
        self.saison: str = list(deck_data.keys())[0]
        self.duelliste: str | None = None
        self._rebuild_components()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Méthodes internes
    # ────────────────────────────────────────────────────────────────────────────

    def _rebuild_components(self):
        """Reconstruit les sélecteurs selon la saison/duelliste courants."""
        self.clear_items()
        self.add_item(SaisonSelect(self))
        self.add_item(DuellisteSelect(self))
        self.add_item(FavoriButton(self))

    def _build_embed(self) -> discord.Embed:
        """Construit l'embed avec les infos du duelliste sélectionné."""
        infos = self.deck_data.get(self.saison, {}).get(self.duelliste, {})
        deck_text = format_deck(infos.get("deck", {}))

        embed = discord.Embed(
            title=f"🎴 Deck de {self.duelliste}",
            description=f"Saison : **{self.saison}**",
            color=discord.Color.gold(),
        )
        embed.add_field(name="📘 Deck(s)", value=deck_text, inline=False)
        return embed

    async def refresh(self, interaction: discord.Interaction):
        """Met à jour le message après un changement de saison ou de duelliste."""
        self._rebuild_components()

        if self.duelliste:
            await interaction.response.edit_message(
                content=f"📅 Saison : **{self.saison}**",
                embed=self._build_embed(),
                view=self,
            )
        else:
            await interaction.response.edit_message(
                content=f"📅 Saison : **{self.saison}** — Sélectionne un duelliste :",
                embed=None,
                view=self,
            )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Deck(commands.Cog):
    """Commande /vaact_deck et !vaact_deck — Consultation des decks VAACT."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.deck_data: dict = load_deck_data()  # chargé une fois au démarrage du bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="vaact_deck", description="Choisis une saison et un duelliste pour voir ses decks")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_deck(self, interaction: discord.Interaction):
        if not self.deck_data:
            return await safe_respond(interaction, "❌ Impossible de charger les decks.")
        view = DeckView(self.deck_data, author_id=interaction.user.id)
        await interaction.response.send_message("📦 Choisis une saison :", view=view, ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="vaact_deck", aliases=["vaaactdeck"], help="Choisis une saison et un duelliste pour voir ses decks")
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_deck(self, ctx: commands.Context):
        if not self.deck_data:
            return await safe_send(ctx.channel, "❌ Impossible de charger les decks.")
        view = DeckView(self.deck_data, author_id=ctx.author.id)
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
