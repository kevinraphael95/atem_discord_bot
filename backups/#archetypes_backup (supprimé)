# ────────────────────────────────────────────────────────────────────────────────
# 📁 archetypes.py — Commande !archetype
# ────────────────────────────────────────────────────────────────────────────────
# Ce module permet d’afficher :
#   1. Une liste paginée des archétypes disponibles
#   2. Les détails d’un archétype spécifique (via recherche)
# Données lues depuis un fichier JSON : "data/archetypes.json"
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 IMPORTS
# ────────────────────────────────────────────────────────────────────────────────
import discord                            # 📦 API Discord
from discord.ext import commands          # 🧩 Extension commandes
import json                               # 📄 Chargement du fichier JSON
import os                                 # 📁 Manipulation de fichiers
import asyncio                            # ⏱️ Gestion des délais pour la pagination

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 COG : ArchetypeCommand
# ────────────────────────────────────────────────────────────────────────────────
class ArchetypeCommand(commands.Cog):
    """
    🃏 Commandes liées aux archétypes Yu-Gi-Oh.
    Permet d’afficher tous les archétypes ou la description d’un en particulier.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot                                      # 🔌 Instance du bot
        self.data_file = "data/archetypes.json"             # 📁 Chemin du fichier JSON
        self.archetypes = self.load_archetypes()            # 📥 Chargement des données à l’init

    # ────────────────────────────────────────────────────────────────────────────
    # 📥 Chargement des archétypes depuis le fichier JSON
    # ────────────────────────────────────────────────────────────────────────────
    def load_archetypes(self):
        if not os.path.exists(self.data_file):
            return {}  # 🚫 Fichier inexistant
        with open(self.data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 COMMANDE : !archetype / !archétype / !arch
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="archetype",
        aliases=["archétype", "arch"],
        help="📚 Affiche la liste des archétypes ou les détails d’un archétype."
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)  # 🧊 Cooldown anti-spam
    async def archetype(self, ctx: commands.Context, *args):
        """
        📘 Affiche la liste des archétypes (paginée) ou les détails d’un archétype donné.
        """

        # 🔍 Aucun archétype chargé
        if not self.archetypes:
            return await ctx.send("⚠️ Aucun archétype n’a été chargé.")

        # ────────────────────────────────────────────────────────────────────────
        # 🔍 RECHERCHE D’UN ARCHÉTYPE PRÉCIS
        # ────────────────────────────────────────────────────────────────────────
        if args:
            query = " ".join(args).lower()
            found = None
            for name, info in self.archetypes.items():
                if query in name.lower():
                    found = (name, info)
                    break

            if found:
                embed = discord.Embed(
                    title=f"📘 Archétype : {found[0]}",
                    description=found[1].get("description", "Aucune description disponible."),
                    color=discord.Color.blue()
                )
                return await ctx.send(embed=embed)
            else:
                return await ctx.send("❌ Archétype non trouvé.")

        # ────────────────────────────────────────────────────────────────────────
        # 📄 AFFICHAGE DE TOUS LES ARCHÉTYPES (PAGINATION)
        # ────────────────────────────────────────────────────────────────────────
        pages = []
        archetype_names = sorted(self.archetypes.keys())  # 🔠 Tri alphabétique
        chunk_size = 5  # 📄 5 noms par page

        # 🔁 Création des pages
        for i in range(0, len(archetype_names), chunk_size):
            chunk = archetype_names[i:i + chunk_size]
            desc = "\n".join([f"• **{name}**" for name in chunk])
            embed = discord.Embed(
                title=f"📚 Archétypes ({i + 1}-{min(i + chunk_size, len(archetype_names))} sur {len(archetype_names)})",
                description=desc,
                color=discord.Color.green()
            )
            pages.append(embed)

        # ⏪ Affiche la première page
        current = 0
        message = await ctx.send(embed=pages[current])

        # ❌ Pas besoin de pagination si une seule page
        if len(pages) <= 1:
            return

        # ⬅️➡️ Ajout des réactions de navigation
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

        # ✅ Fonction de vérification des réactions utilisateur
        def check(reaction, user):
            return (
                user == ctx.author and 
                str(reaction.emoji) in ["⬅️", "➡️"] and 
                reaction.message.id == message.id
            )

        # 🔄 Boucle de pagination (timeout : 60s)
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                await message.remove_reaction(reaction.emoji, user)

                if str(reaction.emoji) == "➡️" and current < len(pages) - 1:
                    current += 1
                    await message.edit(embed=pages[current])
                elif str(reaction.emoji) == "⬅️" and current > 0:
                    current -= 1
                    await message.edit(embed=pages[current])
            except asyncio.TimeoutError:
                break  # ⌛ Fin de la pagination après 60 secondes

    # ────────────────────────────────────────────────────────────────────────────
    # 🏷️ CATEGORISATION dans le !help
    # ────────────────────────────────────────────────────────────────────────────
    def cog_load(self):
        self.archetype.category = "🃏 Yu-Gi-Oh!"

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ SETUP DU COG
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    """
    🔁 Ajoute ce cog au bot au démarrage.
    Associe aussi la catégorie personnalisée "🃏 Yu-Gi-Oh!" pour !help.
    """
    cog = ArchetypeCommand(bot)

    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"

    await bot.add_cog(cog)
    print("✅ Cog chargé : ArchetypeCommand (catégorie = 🃏 Yu-Gi-Oh!)")
