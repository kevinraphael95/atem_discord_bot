# ────────────────────────────────────────────────────────────────────────────────
# 📌 phases.py — Commande interactive !phases
# Objectif : Affiche en détail les différentes phases d’un tour dans Yu-Gi-Oh!
# Catégorie : 🃏 Yu-Gi-Oh!
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Phases(commands.Cog):
    """
    Commande !phases — Affiche le déroulement d’un tour dans Yu-Gi-Oh!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="phases",
        help="Explique en détail les phases d'un tour dans Yu-Gi-Oh!",
        description="Affiche les 6 grandes phases du tour et leurs effets dans Yu-Gi-Oh!"
    )
    async def phases(self, ctx: commands.Context):
        """Commande principale pour afficher le déroulement d’un tour."""
        try:
            embed = discord.Embed(
                title="📜 Le Flux d’un Tour dans Yu-Gi-Oh!",
                description="Voici le déroulement complet d’un tour d’un duelliste. Maîtrise chaque phase si tu veux dominer l’arène.",
                color=discord.Color.dark_red()
            )

            embed.add_field(
                name="🃏 1. Draw Phase — Phase de Pioche",
                value="Tu pioches 1 carte. Certains effets peuvent s'activer ici (ex : *Super Rejuvenation*).",
                inline=False
            )
            embed.add_field(
                name="⏳ 2. Standby Phase — Phase d’Attente",
                value="Des cartes ou effets suspendus prennent effet (ex : *Maintenance Cost*, *Treeborn Frog*, etc.).",
                inline=False
            )
            embed.add_field(
                name="⚙️ 3. Main Phase 1 — Phase Principale 1",
                value=(
                    "**Ce que tu peux faire :**\n"
                    "• Invoquer/Poser un monstre\n"
                    "• Activer des cartes Magie\n"
                    "• Poser des cartes Piège\n"
                    "• Changer la position d’un monstre (1x par monstre)"
                ),
                inline=False
            )
            embed.add_field(
                name="⚔️ 4. Battle Phase — Phase de Combat",
                value="La phase où les duellistes s'affrontent ! Elle contient **5 sous-phases** tactiques.",
                inline=False
            )
            embed.add_field(
                name=" 🔸 a) Start Step",
                value="Déclaration de l'entrée en Battle Phase. Certaines cartes peuvent être activées ici.",
                inline=False
            )
            embed.add_field(
                name=" 🔸 b) Battle Step",
                value="Le joueur **choisit un monstre** et **déclare une attaque**.",
                inline=False
            )
            embed.add_field(
                name=" 🔸 c) Damage Step",
                value=(
                    "Étape clé où se calcule le combat :\n"
                    "• Modifs d’ATK/DEF finales\n"
                    "• Activation de cartes comme **Honest**, **Shrink**, etc.\n"
                    "• Application des effets (destruction, dégâts, triggers)"
                ),
                inline=False
            )
            embed.add_field(
                name=" 🔸 d) End of Damage Step",
                value="Fin des effets liés au combat. Aucun boost de stats ne peut être activé maintenant.",
                inline=False
            )
            embed.add_field(
                name=" 🔸 e) End Step",
                value="Le joueur peut choisir un autre monstre pour attaquer ou quitter la Battle Phase.",
                inline=False
            )
            embed.add_field(
                name="🔧 5. Main Phase 2 — Phase Principale 2",
                value="Identique à la Main Phase 1 (sauf invocation normale si déjà faite). Tu peux poser ou activer des cartes.",
                inline=False
            )
            embed.add_field(
                name="🌙 6. End Phase — Phase de Fin",
                value="Le tour se termine. Certains effets s’activent maintenant (effets temporisés, défausse si >6 cartes).",
                inline=False
            )

            embed.set_footer(text="🎴 Une seule erreur peut t’envoyer dans le Royaume des Ombres. Sois prêt, duelliste.")
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"[ERREUR phases] {e}")
            await ctx.send("❌ Une erreur est survenue lors de l’affichage des phases.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Phases(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Test"
    await bot.add_cog(cog)
