# ────────────────────────────────────────────────────────────────────────────────
# 📌 help.py — Commande interactive !help et /help
# Objectif : Afficher dynamiquement l’aide des commandes par catégories avec boutons
# Catégorie : Général
# Accès : Public
# Cooldown : 1 utilisation / 5 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import math
from bot import get_prefix
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — View principale (pagination + catégories)
# ────────────────────────────────────────────────────────────────────────────────
class HelpView(View):
    def __init__(self, bot, categories, prefix, user_id, category="Général"):
        super().__init__(timeout=120)
        self.bot = bot
        self.categories = categories
        self.prefix = prefix
        self.category = category
        self.user_id = user_id
        self.commands = sorted(categories.get(category, []), key=lambda c: c.name)

        self.page = 0
        self.per_page = 8
        self.total_pages = max(1, math.ceil(len(self.commands) / self.per_page))
        self.message = None

        # Boutons pagination
        self.add_item(PrevButton(self))
        self.add_item(NextButton(self))

        # Boutons catégories
        for cat, cmds in sorted(categories.items()):
            self.add_item(CategoryButton(cat, len(cmds), self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Tu n'es pas autorisé à utiliser ces boutons.", ephemeral=True
            )
            return False
        return True

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"📂 {self.category}",
            description=f"Page {self.page + 1}/{self.total_pages}",
            color=discord.Color.blurple()
        )
        start = self.page * self.per_page
        end = start + self.per_page
        for cmd in self.commands[start:end]:
            embed.add_field(
                name=f"`{self.prefix}{cmd.name}`",
                value=cmd.help or "Pas de description.",
                inline=False
            )
        embed.set_footer(text=f"{self.prefix}help <commande> pour plus de détails")
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# ⏮️ Bouton précédent
# ────────────────────────────────────────────────────────────────────────────────
class PrevButton(Button):
    def __init__(self, view: HelpView):
        super().__init__(emoji="◀️", style=discord.ButtonStyle.primary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.view_ref.page > 0:
            self.view_ref.page -= 1
            await safe_edit(interaction.message, embed=self.view_ref.build_embed(), view=self.view_ref)

# ────────────────────────────────────────────────────────────────────────────────
# ⏭️ Bouton suivant
# ────────────────────────────────────────────────────────────────────────────────
class NextButton(Button):
    def __init__(self, view: HelpView):
        super().__init__(emoji="▶️", style=discord.ButtonStyle.primary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.view_ref.page < self.view_ref.total_pages - 1:
            self.view_ref.page += 1
            await safe_edit(interaction.message, embed=self.view_ref.build_embed(), view=self.view_ref)

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Bouton catégorie
# ────────────────────────────────────────────────────────────────────────────────
class CategoryButton(Button):
    def __init__(self, category: str, count: int, view: HelpView):
        style = discord.ButtonStyle.success if category == view.category else discord.ButtonStyle.secondary
        super().__init__(label=f"{category} ({count})", style=style)
        self.category = category
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view_ref.category = self.category
        self.view_ref.commands = sorted(self.view_ref.categories.get(self.category, []), key=lambda c: c.name)
        self.view_ref.page = 0
        self.view_ref.total_pages = max(1, math.ceil(len(self.view_ref.commands) / self.view_ref.per_page))

        # Refresh boutons
        self.view_ref.clear_items()
        self.view_ref.add_item(PrevButton(self.view_ref))
        self.view_ref.add_item(NextButton(self.view_ref))
        for cat, cmds in sorted(self.view_ref.categories.items()):
            self.view_ref.add_item(CategoryButton(cat, len(cmds), self.view_ref))

        await safe_edit(interaction.message, embed=self.view_ref.build_embed(), view=self.view_ref)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class HelpCommand(commands.Cog):
    """Commande !help et /help — Aide interactive par boutons"""

    def __init__(self, bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ──────────────────────────────────────────────────────────────
    @commands.command(name="help", aliases=["h"], help="Affiche l’aide du bot.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help_func(self, ctx: commands.Context, commande: str = None):
        await self._send_help(ctx.author.id, ctx.channel, commande)

    # ──────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ──────────────────────────────────────────────────────────────
    @app_commands.command(name="help", description="Affiche l’aide interactive du bot.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_help(self, interaction: discord.Interaction, commande: str = None):
        await interaction.response.defer()
        await self._send_help(interaction.user.id, interaction.channel, commande)
        await interaction.delete_original_response()

    # ──────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ──────────────────────────────────────────────────────────────
    async def _send_help(self, user_id: int, channel, commande: str = None):
        prefix = get_prefix(self.bot, None)

        if commande:
            cmd = self.bot.get_command(commande)
            if not cmd:
                await safe_send(channel, f"❌ Commande `{commande}` inconnue.")
                return
            embed = discord.Embed(title=f"ℹ️ `{prefix}{cmd.name}`", color=discord.Color.green())
            embed.add_field(name="📄 Description", value=cmd.help or "Aucune description.", inline=False)
            if cmd.aliases:
                embed.add_field(name="🔁 Alias", value=", ".join(f"`{a}`" for a in cmd.aliases), inline=False)
            await safe_send(channel, embed=embed)
            return

        # Regroupement par catégories
        categories = {}
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue
            cat = getattr(cmd, "category", "Autres")
            categories.setdefault(cat, []).append(cmd)

        view = HelpView(self.bot, categories, prefix, user_id, category="Général")
        message = await safe_send(channel, embed=view.build_embed(), view=view)
        view.message = message

# ──────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ──────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = HelpCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
    print("✅ Cog chargé : HelpCommand (slash + boutons interactifs)")
