# ────────────────────────────────────────────────────────────────────────────────
# 📌 help.py — Commande interactive !help (version boutons)
# Objectif : Afficher dynamiquement l’aide des commandes par catégories
# Catégorie : Général
# Accès : Public
# Cooldown : 1 utilisation / 5 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
from bot import get_prefix
import math
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Boutons catégories
# ────────────────────────────────────────────────────────────────────────────────
class HelpCategoryView(View):
    def __init__(self, bot, categories, prefix):
        super().__init__(timeout=120)
        self.bot = bot
        self.categories = categories
        self.prefix = prefix

        for cat, cmds in sorted(categories.items()):
            self.add_item(CategoryButton(cat, cmds, bot, prefix, self))

class CategoryButton(Button):
    def __init__(self, category, commands_list, bot, prefix, parent_view):
        super().__init__(
            label=f"{category} ({len(commands_list)})",
            style=discord.ButtonStyle.secondary
        )
        self.category = category
        self.commands_list = sorted(commands_list, key=lambda c: c.name)
        self.bot = bot
        self.prefix = prefix
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        paginator = HelpPaginatorView(
            self.bot,
            self.category,
            self.commands_list,
            self.prefix,
            self.parent_view
        )
        await safe_edit(
            interaction.message,
            embed=paginator.create_embed(),
            view=paginator
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Pagination commandes
# ────────────────────────────────────────────────────────────────────────────────
class HelpPaginatorView(View):
    def __init__(self, bot, category, commands_list, prefix, parent_view):
        super().__init__(timeout=120)
        self.bot = bot
        self.category = category
        self.commands = commands_list
        self.prefix = prefix
        self.parent_view = parent_view
        self.page = 0
        self.per_page = 8
        self.total_pages = max(1, math.ceil(len(self.commands) / self.per_page))

        if self.total_pages > 1:
            self.add_item(PrevButton(self))
            self.add_item(NextButton(self))

        self.add_item(BackButton(self.parent_view))

    def create_embed(self):
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

class PrevButton(Button):
    def __init__(self, paginator):
        super().__init__(emoji="◀", style=discord.ButtonStyle.primary)
        self.paginator = paginator

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.paginator.page > 0:
            self.paginator.page -= 1
            await safe_edit(
                interaction.message,
                embed=self.paginator.create_embed(),
                view=self.paginator
            )

class NextButton(Button):
    def __init__(self, paginator):
        super().__init__(emoji="▶", style=discord.ButtonStyle.primary)
        self.paginator = paginator

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.paginator.page < self.paginator.total_pages - 1:
            self.paginator.page += 1
            await safe_edit(
                interaction.message,
                embed=self.paginator.create_embed(),
                view=self.paginator
            )

class BackButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="🔙 Catégories", style=discord.ButtonStyle.danger)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await safe_edit(
            interaction.message,
            content="📌 Choisis une catégorie :",
            embed=None,
            view=self.parent_view
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class HelpCommand(commands.Cog):
    """Commande !help — Aide interactive par boutons"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h"], help="Affiche l’aide du bot.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help_func(self, ctx: commands.Context, commande: str = None):
        prefix = get_prefix(self.bot, ctx.message)

        if commande:
            cmd = self.bot.get_command(commande)
            if not cmd:
                return await safe_send(ctx.channel, f"❌ Commande `{commande}` inconnue.")

            embed = discord.Embed(
                title=f"ℹ️ `{prefix}{cmd.name}`",
                color=discord.Color.green()
            )
            embed.add_field(name="📄 Description", value=cmd.help or "Aucune.", inline=False)
            if cmd.aliases:
                embed.add_field(
                    name="🔁 Alias",
                    value=", ".join(f"`{a}`" for a in cmd.aliases),
                    inline=False
                )
            return await safe_send(ctx.channel, embed=embed)

        categories = {}
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue
            cat = getattr(cmd, "category", "Autres")
            categories.setdefault(cat, []).append(cmd)

        view = HelpCategoryView(self.bot, categories, prefix)
        await safe_send(ctx.channel, "📌 Choisis une catégorie :", view=view)

    def cog_load(self):
        self.help_func.category = "Général"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = HelpCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
    print("✅ Cog chargé : HelpCommand (boutons)")
