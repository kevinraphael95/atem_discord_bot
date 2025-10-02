# ────────────────────────────────────────────────────────────────────────────────
# 📌 deck.py — Commande interactive /deck et !deck
# Objectif : Afficher un deck depuis un fichier .ydk
# Catégorie : Autre
# Accès : Tous
# Cooldown : Paramétrable par commande
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands, File, Embed, Interaction, ButtonStyle
from discord.ext import commands
from discord.ui import View, Button
from io import BytesIO
import aiohttp
import os

from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class DeckCog(commands.Cog):
    """
    Commande /deck et !deck — Affiche un deck depuis un fichier .ydk
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 🔹 Récupère les cartes depuis l'API
    async def get_cards(self, cards: set[int]) -> dict:
        async with aiohttp.ClientSession() as session:
            url = f"{os.getenv('API_URL')}/ocg-tcg/multi?password={','.join(map(str, cards))}"
            async with session.get(url) as resp:
                return await resp.json()

    # 🔹 Parse un fichier .ydk en dictionnaire interne
    async def parse_file(self, attachment: discord.Attachment) -> dict:
        if not attachment.filename.endswith(".ydk"):
            raise ValueError(".ydk files must have the .ydk extension!")
        if attachment.size > 1024:
            raise ValueError(".ydk files should not exceed 1 KB!")
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                content = await resp.text()
        # Décomposition simple du fichier .ydk
        sections = {"main": [], "extra": [], "side": []}
        current_section = "main"
        for line in content.splitlines():
            line = line.strip()
            if line == "":
                continue
            if line == "#extra":
                current_section = "extra"
                continue
            if line == "!side":
                current_section = "side"
                continue
            if line.isdigit():
                sections[current_section].append(int(line))
        return sections

    # 🔹 Génère l'embed du deck
    def generate_embed(self, deck: dict, card_data: dict, stacked: bool) -> Embed:
        embed = Embed(title="Your Deck", color=discord.Color.blue())

        def add_section(name: str, cards_list: list):
            counts = {}
            for c in cards_list:
                name_card = card_data.get(str(c), {}).get("name", str(c))
                counts[name_card] = counts.get(name_card, 0) + 1
            lines = [f"{v} {k}" for k, v in counts.items()]
            embed.add_field(name=name, value="\n".join(lines), inline=not stacked)

        if deck["main"]:
            add_section(f"Main Deck ({len(deck['main'])} cards)", deck["main"])
        if deck["extra"]:
            add_section(f"Extra Deck ({len(deck['extra'])} cards)", deck["extra"])
        if deck["side"]:
            add_section(f"Side Deck ({len(deck['side'])} cards)", deck["side"])

        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="deck", description="Afficher un deck depuis un fichier .ydk")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_deck(
        self,
        interaction: Interaction,
        public: bool = False
    ):
        await interaction.response.defer(ephemeral=not public)

        if not interaction.data.get("attachments"):
            await interaction.edit_original_response(content="❌ Vous devez fournir un fichier .ydk")
            return

        attachment = interaction.data["attachments"][0]

        try:
            deck = await self.parse_file(discord.Attachment(state=None, data=attachment))
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Erreur: {e}")
            return

        if sum(len(deck[x]) for x in ["main", "extra", "side"]) == 0:
            await interaction.edit_original_response(content="❌ Erreur: deck vide")
            return

        passwords = set(deck["main"] + deck["extra"] + deck["side"])
        card_data = await self.get_cards(passwords)
        embed = self.generate_embed(deck, card_data, stacked=False)

        # Création du fichier .ydk pour renvoi
        ydk_lines = [str(c) for c in deck["main"]] + ["#extra"] + [str(c) for c in deck["extra"]] + ["!side"] + [str(c) for c in deck["side"]]
        file_obj = File(BytesIO("\n".join(ydk_lines).encode("utf-8")), filename="deck.ydk")

        view = View()
        view.add_item(
            Button(
                label="Upload to YGOPRODECK",
                url="https://ygoprodeck.com/deckbuilder/",
                style=ButtonStyle.link
            )
        )

        await interaction.edit_original_response(embed=embed, file=file_obj, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="deck")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_deck(self, ctx: commands.Context):
        class DummyInteraction:
            data = ctx.message.attachments
            async def response(self): return ctx
            async def edit_original_response(self, **kwargs): await ctx.send(**kwargs)
        await self.slash_deck(DummyInteraction())

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = DeckCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Autre"
    await bot.add_cog(cog)
