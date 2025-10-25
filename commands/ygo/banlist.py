# ────────────────────────────────────────────────────────────────────────────────
# 📌 banlist.py — Affiche la banlist TCG/OCG paginée avec navigation
# Objectif : Commande pour voir les cartes bannies, limitées et semi-limitées avec pagination interactive
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from utils.discord_utils import safe_send, safe_respond
import aiohttp
import math

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Banlist(commands.Cog):
    """
    Commande /banlist et !banlist — Affiche la banlist TCG ou OCG avec navigation par boutons.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="banlist",
        description="Affiche la banlist TCG ou OCG avec pagination interactive."
    )
    @app_commands.describe(format="Choisissez TCG ou OCG")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_banlist(self, interaction: discord.Interaction, format: str = "TCG"):
        await self.fetch_and_send(interaction, format.upper())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="banlist")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_banlist(self, ctx: commands.Context, format: str = "TCG"):
        await self.fetch_and_send(ctx, format.upper())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction principale
    # ────────────────────────────────────────────────────────────────────────────
    async def fetch_and_send(self, ctx_or_inter, format_name: str):
        valid_formats = ["TCG", "OCG"]
        if format_name not in valid_formats:
            return await safe_respond(ctx_or_inter, f"❌ Format invalide. Utilisez TCG ou OCG.")

        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?banlist={format_name.lower()}&language=fr"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await safe_respond(ctx_or_inter, "❌ Impossible de récupérer la banlist.")
                data_json = await resp.json()

        cards = data_json.get("data", [])
        if not cards:
            return await safe_respond(ctx_or_inter, f"❌ Aucune carte trouvée pour {format_name}.")

        # ──────────────── Trier par catégorie ────────────────
        banned, limited, semi_limited = [], [], []
        for card in cards:
            # L'API récente place le banlist dans banlist_info
            ban_info = card.get("banlist_info", {})
            ban_status = ban_info.get(format_name.lower(), "").lower()
            entry = {
                "name": card["name"],
                "img": card["card_images"][0]["image_url_cropped"] if card.get("card_images") else None
            }
            if ban_status == "forbidden":
                banned.append(entry)
            elif ban_status == "limited":
                limited.append(entry)
            elif ban_status == "semi-limited":
                semi_limited.append(entry)

        categories = [
            ("⛔ Bannies", banned, discord.Color.red()),
            ("⚠️ Limitées", limited, discord.Color.orange()),
            ("⚖️ Semi-Limitées", semi_limited, discord.Color.gold())
        ]

        # ──────────────── Créer les embeds paginés ────────────────
        embeds = []
        per_page = 20
        for title, card_list, color in categories:
            if not card_list:
                continue
            card_list.sort(key=lambda x: x["name"])
            total_pages = math.ceil(len(card_list) / per_page)
            for page in range(total_pages):
                start = page * per_page
                end = start + per_page
                page_cards = card_list[start:end]
                embed = discord.Embed(
                    title=f"{title} ({format_name}) — Page {page+1}/{total_pages}",
                    description="\n".join([f"**{c['name']}**" for c in page_cards]),
                    color=color
                )
                embed.set_thumbnail(url=page_cards[0]["img"] if page_cards[0]["img"] else discord.Embed.Empty)
                embed.set_footer(text=f"Source: YGOPRODeck")
                embeds.append(embed)

        # ──────────────── Vue de navigation ────────────────
        class PaginationView(View):
            def __init__(self, embeds_list):
                super().__init__(timeout=120)
                self.embeds = embeds_list
                self.index = 0

            @discord.ui.button(label="◀️", style=discord.ButtonStyle.gray)
            async def previous(self, interaction: discord.Interaction, button: Button):
                if self.index > 0:
                    self.index -= 1
                    await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

            @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray)
            async def next(self, interaction: discord.Interaction, button: Button):
                if self.index < len(self.embeds) - 1:
                    self.index += 1
                    await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

        # ──────────────── Envoi initial ────────────────
        if not embeds:
            return await safe_respond(ctx_or_inter, f"❌ Aucune carte trouvée pour {format_name}.")
        view = PaginationView(embeds)
        await safe_send(ctx_or_inter.channel if hasattr(ctx_or_inter, "channel") else ctx_or_inter,
                        embed=embeds[0], view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Banlist(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
