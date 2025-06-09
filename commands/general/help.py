# ────────────────────────────────────────────────────────────────────────────────
# 📌 help.py — Commande interactive !help
# Objectif : Afficher dynamiquement l’aide des commandes avec menu déroulant par catégorie et pagination
# Catégorie : Général
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import math
import os

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Menu déroulant de sélection de catégorie
# ────────────────────────────────────────────────────────────────────────────────
class HelpCategoryView(View):
    def __init__(self, bot, categories, prefix):
        super().__init__(timeout=None)  # Pas de timeout
        self.bot = bot
        self.categories = categories
        self.prefix = prefix
        self.add_item(HelpCategorySelect(self))

class HelpCategorySelect(Select):
    def __init__(self, parent_view: HelpCategoryView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=cat, description=f"{len(cmds)} commande(s)")
            for cat, cmds in sorted(self.parent_view.categories.items())
        ]
        super().__init__(placeholder="Sélectionne une catégorie", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_cat = self.values[0]
        commands_in_cat = self.parent_view.categories[selected_cat]
        commands_in_cat.sort(key=lambda c: c.name)

        paginator = HelpPaginatorView(
            self.parent_view.bot,
            selected_cat,
            commands_in_cat,
            self.parent_view.prefix,
            self.parent_view  # Pour pouvoir revenir au menu catégories
        )

        await interaction.response.edit_message(
            content=f"📂 Catégorie sélectionnée : **{selected_cat}**",
            embed=paginator.create_embed(),
            view=paginator
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Pagination des commandes dans une catégorie
# ────────────────────────────────────────────────────────────────────────────────
class HelpPaginatorView(View):
    def __init__(self, bot, category, commands_list, prefix, parent_view):
        super().__init__(timeout=None)
        self.bot = bot
        self.category = category
        self.commands = commands_list
        self.prefix = prefix
        self.parent_view = parent_view
        self.page = 0
        self.per_page = 10
        self.total_pages = math.ceil(len(self.commands) / self.per_page)

        if self.total_pages > 1:
            self.add_item(PrevButton(self))
            self.add_item(NextButton(self))

        # On remet le menu déroulant pour changer de catégorie
        self.add_item(HelpCategorySelect(self.parent_view))

    def create_embed(self):
        embed = discord.Embed(
            title=f"📂 {self.category} — Page {self.page + 1}/{self.total_pages}",
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
        embed.set_footer(text=f"Utilise {self.prefix}help <commande> pour plus de détails.")
        return embed

class PrevButton(Button):
    def __init__(self, paginator):
        super().__init__(label="◀️", style=discord.ButtonStyle.primary)
        self.paginator = paginator

    async def callback(self, interaction: discord.Interaction):
        if self.paginator.page > 0:
            self.paginator.page -= 1
            await interaction.response.edit_message(embed=self.paginator.create_embed(), view=self.paginator)

class NextButton(Button):
    def __init__(self, paginator):
        super().__init__(label="▶️", style=discord.ButtonStyle.primary)
        self.paginator = paginator

    async def callback(self, interaction: discord.Interaction):
        if self.paginator.page < self.paginator.total_pages - 1:
            self.paginator.page += 1
            await interaction.response.edit_message(embed=self.paginator.create_embed(), view=self.paginator)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — Help
# ────────────────────────────────────────────────────────────────────────────────
class Help(commands.Cog):
    """
    📚 Commande !help : système d’aide contextuelle avec menu déroulant
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="help",
        aliases=["aide", "h"],
        help="Affiche la liste des commandes ou les infos d’une commande spécifique.",
        description=(
            "📌 Utilisation : `!help` ou `!help <commande>`\n"
            "- Sans argument : liste complète des commandes avec menu déroulant\n"
            "- Avec un nom : détails complets de la commande"
        )
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def help_func(self, ctx: commands.Context, commande: str = None):
        prefix = os.getenv("COMMAND_PREFIX", "!")

        if commande:
            cmd = self.bot.get_command(commande)
            if not cmd:
                await ctx.send(f"❌ La commande `{commande}` n’existe pas.")
                return

            embed = discord.Embed(
                title=f"ℹ️ Aide pour : `{prefix}{cmd.name}`",
                color=discord.Color.blue()
            )
            embed.add_field(name="📝 Description", value=cmd.help or "Pas de description disponible.", inline=False)
            if cmd.aliases:
                embed.add_field(name="🔁 Alias", value=", ".join(f"`{a}`" for a in cmd.aliases), inline=False)
            embed.set_footer(text="📌 <obligatoire> — [optionnel]")
            await ctx.send(embed=embed)
            return

        # Sans argument, affichage interactif par catégories
        categories = {}
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue
            cat = getattr(cmd, "category", "Autres")
            categories.setdefault(cat, []).append(cmd)

        view = HelpCategoryView(self.bot, categories, prefix)
        await ctx.send("📌 Sélectionne une catégorie pour voir ses commandes :", view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Help(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
