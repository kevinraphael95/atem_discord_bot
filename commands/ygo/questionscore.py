# ────────────────────────────────────────────────────────────────────────────────
# 🔥 streak.py — Commande !streak
# Objectif : Afficher la série actuelle et le meilleur record de bonnes réponses
# Catégorie : "🧠 VAACT"
# Base de données : Supabase (table "ygo_streaks")
# Langue : 🇫🇷 Français uniquement
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord                                 # Pour envoyer des messages embed ou texte
from discord.ext import commands              # Pour créer une commande dans un Cog
from supabase_client import supabase          # Client Supabase déjà configuré et connecté

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — Gestion de la commande !streak
# ────────────────────────────────────────────────────────────────────────────────
class Streak(commands.Cog):
    """
    📊 Commande !streak : affiche la série de bonnes réponses actuelles et le record utilisateur.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot  # 🔗 Référence au bot principal

    # ────────────────────────────────────────────────────────────────────────────
    # 📈 Commande !streak — Affiche la progression de l'utilisateur
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="questionscore",                           # 🔤 Nom principal de la commande
        aliases=["qs", "questionstreak"],      # 🪪 Alias secondaires : !qs fonctionne aussi
        help="Affiche ta série de bonnes réponses."      # 📚 Aide courte
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)  # 🧊 Anti-spam : 1 appel / 3s / utilisateur
    async def streak(self, ctx: commands.Context):
        """
        🔍 Cherche dans Supabase la série de bonnes réponses (streak) pour l’utilisateur,
        puis affiche l’info sous forme de message.
        """

        user_id = str(ctx.author.id)  # 🆔 Identifiant utilisateur Discord (en string pour requête Supabase)

        try:
            # ────────────────────────────────────────────────────────────────────
            # 📦 Requête Supabase — table "ygo_streaks"
            # Objectif : récupérer les champs current_streak et best_streak
            # Filtrage sur : user_id == ID de l'utilisateur appelant
            # ────────────────────────────────────────────────────────────────────
            response = supabase.table("ygo_streaks") \
                .select("current_streak", "best_streak") \
                .eq("user_id", user_id) \
                .execute()

            # ✅ Si des données existent pour cet utilisateur
            if response.data:
                streak = response.data[0]  # 📄 On récupère la première ligne (il ne devrait y en avoir qu'une)
                current = streak.get("current_streak", 0)  # 🔁 Streak actuel
                best = streak.get("best_streak", 0)        # 🏆 Meilleur record

                # 💬 Message personnalisé avec le nom d'affichage
                await ctx.send(
                    f"🔥 **{ctx.author.display_name}**, ta série actuelle est de **{current}** 🔁\n"
                    f"🏆 Ton record absolu est de **{best}** bonnes réponses consécutives !"
                )

            else:
                # ⛔ L'utilisateur n'a pas encore de streak enregistré
                await ctx.send(
                    "📉 Tu n'as pas encore commencé de série.\n"
                    "Lance une question avec `!question` pour démarrer ton streak !"
                )

        except Exception as e:
            # 🚨 Gestion d’erreur (log côté serveur + message utilisateur)
            print("[ERREUR STREAK]", e)
            await ctx.send("🚨 Une erreur est survenue en récupérant ta série.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Fonction de setup du Cog
# Objectif : Enregistrer le Cog et attribuer la catégorie "🧠 VAACT"
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    """
    🔧 Fonction de chargement du Cog Streak.
    Attribue la catégorie personnalisée "🃏 Yu-Gi-Oh!" pour l’aide du bot.
    """
    cog = Streak(bot)

    # 📁 Attribution de la catégorie personnalisée (utile si tu as une commande d’aide personnalisée)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"

    await bot.add_cog(cog)
