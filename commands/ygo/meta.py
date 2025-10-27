# ────────────────────────────────────────────────────────────────────────────────
# 📌 latest.py — Commande interactive !latest
# Objectif :
#   - Afficher les X dernières cartes ajoutées dans la base YGOPRODeck
#   - Navigation interactive entre les cartes
#   - Utilise utils/card_utils pour toutes les requêtes API
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send
from utils.card_utils import fetch_latest_cards, translate_card_type, pick_embed_color, format_attribute, format_race

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View — Pagination interactive des dernières cartes
# ────────────────────────────────────────────────────────────────────────────────
class LatestPagination(View):
    """Navigation interactive entre les dernières cartes ajoutées."""

    def __init__(self, cards: list[dict]):
        super().__init__(timeout=120)
        self.cards = cards
        self.index = 0

    async def update_embed(self, interaction: discord.Interaction):
        carte = self.cards[self.index]
        card_name = carte.get("name", "Carte inconnue")
        type_raw = carte.get("type", "")
        race = carte.get("race", "")
        attr = carte.get("attribute", "")
        desc = carte.get("desc", "Pas de description disponible.")
        atk = carte.get("atk")
        defe = carte.get("def")
        level = carte.get("level")
        rank = carte.get("rank")
        linkval = carte.get("linkval") or carte.get("link_rating")

        card_type_fr = translate_card_type(type_raw)
        color = pick_embed_color(type_raw)

        lines = [f"**Type de carte** : {card_type_fr}"]
        if race:
            lines.append(f"**Type** : {format_race(race)}")
        if attr:
            lines.append(f"**Attribut** : {format_attribute(attr)}")
        if linkval:
            lines.append(f"**Lien** : 🔗 {linkval}")
        elif rank:
            lines.append(f"**Niveau/Rang** : ⭐ {rank}")
        elif level:
            lines.append(f"**Niveau/Rang** : ⭐ {level}")
        if atk is not None or defe is not None:
            atk_text = f"⚔️ {atk}" if atk is not None else "⚔️ ?"
            def_text = f"🛡️ {defe}" if defe is not None else "🛡️ ?"
            lines.append(f"**ATK/DEF** : {atk_text}/{def_text}")
        lines.append(f"**Description**\n{desc}")

        embed = discord.Embed(
            title=f"**{card_name}** — Carte {self.index + 1}/{len(self.cards)}",
            description="\n".join(lines),
            color=color
        )

        if "card_images" in carte and carte["card_images"]:
            thumb = carte["card_images"][0].get("image_url_cropped")
            if thumb:
                embed.set_thumbnail(url=thumb)

        embed.set_footer(text=f"ID Carte : {carte.get('id', '?')} | ID Konami : {carte.get('konami_id', '?')}")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.cards)
        await self.update_embed(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(self.cards)
        await self.update_embed(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Latest(commands.Cog):
    """Commande !latest — Affiche les dernières cartes ajoutées Yu-Gi-Oh!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="latest",
        help="🆕 Affiche les dernières cartes ajoutées dans la base YGOPRODeck."
    )
    async def latest(self, ctx: commands.Context, limit: int = 10):
        """Limit facultatif — par défaut 10 dernières cartes"""
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50  # sécurité

        cards = await fetch_latest_cards(limit)
        if not cards:
            await safe_send(ctx, "❌ Impossible de récupérer les dernières cartes.")
            return

        # Premier embed
        carte = cards[0]
        embed_lines = [
            f"**Type de carte** : {translate_card_type(carte.get('type', ''))}",
            f"**Description** : {carte.get('desc', 'Pas de description disponible.')}"
        ]
        embed = discord.Embed(
            title=f"**{carte.get('name', 'Carte inconnue')}** — Carte 1/{len(cards)}",
            description="\n".join(embed_lines),
            color=pick_embed_color(carte.get('type', ''))
        )
        if "card_images" in carte and carte["card_images"]:
            thumb = carte["card_images"][0].get("image_url_cropped")
            if thumb:
                embed.set_thumbnail(url=thumb)

        await safe_send(ctx, embed=embed, view=LatestPagination(cards))

    def cog_load(self):
        self.latest.category = "🃏 Yu-Gi-Oh!"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Latest(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
