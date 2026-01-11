# ────────────────────────────────────────────────────────────────────────────────
# 📌 commandslist.py — Commande /readme et !readme
# Objectif : Génère un README.md avec toutes les commandes triées et formatées
# Catégorie : Admin
# Accès : Administrateurs seulement
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import io
from utils.discord_utils import safe_send, safe_respond  

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CommandsList(commands.Cog):
    """
    Commande /readme et !readme — Génère un README.md complet avec toutes les commandes.
    Accessible uniquement aux administrateurs.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour générer le contenu Markdown
    # ────────────────────────────────────────────────────────────────────────────
    def build_markdown_content(self) -> str:
        """Renvoie le contenu Markdown complet pour README.md avec format compact et lisible"""
        content = "Liste des Commandes\n\n"

        # Regrouper les commandes par catégorie
        categories = {}
        for cmd in self.bot.commands:
            cat = getattr(cmd, "category", "Autre")
            desc = cmd.help if cmd.help else "Pas de description."
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((cmd.name, desc))

        # Trier les catégories par ordre alphabétique
        for cat in sorted(categories.keys(), key=lambda c: c.lower()):
            content += f"### 📂 {cat}\n"
            for name, desc in sorted(categories[cat], key=lambda x: x[0].lower()):
                content += f"- **{name} :** {desc}\n"
            content += "\n"

        return content

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH (admin uniquement)
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="commandslist",
        description="Génère un .md avec toutes les commandes et les envoie en fichier."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_readme(self, interaction: discord.Interaction):
        try:
            markdown_content = self.build_markdown_content()
            file = discord.File(io.StringIO(markdown_content), filename="Liste des Commandes.md")
            await safe_respond(interaction, "📄 Voici le Liste des Commandes.md avec toutes les commandes :", file=file)
        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /readme] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX (admin uniquement)
    # ────────────────────────────────────────────────────────────────────────────
    @commands.has_permissions(administrator=True)
    @commands.command(
        name="commandslist",
        help="Génère un .md avec toutes les commandes et les envoie en fichier."
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_readme(self, ctx: commands.Context):
        try:
            markdown_content = self.build_markdown_content()
            file = discord.File(io.StringIO(markdown_content), filename="Liste des Commandes.md")
            await safe_send(ctx.channel, "📄 Voici le Liste des Commandes.md avec toutes les commandes :", file=file)
        except commands.CommandOnCooldown as e:
            await safe_send(ctx.channel, f"⏳ Attends encore {e.retry_after:.1f}s.")
        except Exception as e:
            print(f"[ERREUR !readme] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CommandsList(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
