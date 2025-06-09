# ────────────────────────────────────────────────────────────────────────────────
# 🏆 topqs.py — Commande !topqs
# Objectif : Afficher le top 10 des meilleures séries de bonnes réponses (streak)
# Source : Table Supabase "ygo_streaks"
# Langue : 🇫🇷 Français uniquement
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord                                 # Pour créer des embeds Discord
from discord.ext import commands              # Pour créer des commandes dans un Cog
from supabase_client import supabase          # Client Supabase configuré (connexion active)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — Gestion de la commande !topqs
# ────────────────────────────────────────────────────────────────────────────────
class TopQS(commands.Cog):
    """
    🏅 Commande !topqs : affiche le classement des meilleurs streaks de bonnes réponses.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot  # 🔗 Référence au bot principal

    # ────────────────────────────────────────────────────────────────────────────
    # 📈 Commande !topqs — Top 10 meilleurs streaks
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="questionscoretop",                                     # Nom principal de la commande
        aliases=["qst", "qstop"],                    # Alias utilisables
        help="Affiche le classement des meilleures séries de bonnes réponses."  # Aide courte
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)  # 🧊 Anti-spam : 1 appel / 3s / utilisateur
    async def topqs(self, ctx: commands.Context):
        """
        📊 Récupère depuis Supabase le top 10 des utilisateurs ayant les meilleurs streaks.
        """

        try:
            # ────────────────────────────────────────────────────────────────────
            # 🔎 Requête Supabase : on trie les utilisateurs par best_streak DESC
            # ────────────────────────────────────────────────────────────────────
            response = supabase.table("ygo_streaks") \
                .select("user_id, best_streak") \
                .order("best_streak", desc=True) \
                .limit(10) \
                .execute()

            # 📉 Si aucun résultat (aucun streak enregistré)
            if not response.data:
                await ctx.send("📉 Aucun streak enregistré pour le moment.")
                return

            # ────────────────────────────────────────────────────────────────────
            # 🏅 Construction du classement
            # ────────────────────────────────────────────────────────────────────
            leaderboard = []  # 🧾 Liste qui contiendra les lignes du classement

            for index, row in enumerate(response.data, start=1):
                user_id = row["user_id"]
                best_streak = row.get("best_streak", 0)

                try:
                    # 👤 On tente de récupérer le nom Discord de l'utilisateur
                    user = await self.bot.fetch_user(int(user_id))
                    username = user.name if user else f"Utilisateur inconnu ({user_id})"
                except:
                    # ❓ Si utilisateur introuvable (peut-être a-t-il quitté le serveur)
                    username = f"Utilisateur inconnu ({user_id})"

                # 🥇🥈🥉 Icônes spéciales pour les 3 premiers
                place = {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, f"`#{index}`")

                # ➕ Ajout de la ligne dans le classement
                leaderboard.append(f"{place} **{username}** : 🔥 {best_streak}")

            # ────────────────────────────────────────────────────────────────────
            # 🖼️ Création de l'embed de réponse avec le top 10
            # ────────────────────────────────────────────────────────────────────
            embed = discord.Embed(
                title="🏆 Top 10 – Meilleures Séries",
                description="\n".join(leaderboard),  # 🪄 Ajoute les lignes une à une
                color=discord.Color.gold()
            )
            embed.set_footer(text="Classement basé sur la meilleure série atteinte.")

            # 📤 Envoi du classement dans le salon
            await ctx.send(embed=embed)

        except Exception as e:
            # 🚨 Gestion d’erreur (log + message utilisateur)
            print("[ERREUR TOPQS]", e)
            await ctx.send("🚨 Une erreur est survenue lors du classement.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Fonction de setup du Cog
# Objectif : Charger le cog et l’ajouter dans une catégorie personnalisée
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    """
    🔧 Fonction d'enregistrement du Cog TopQS.
    Attribue la catégorie '🃏 Yu-Gi-Oh!' si aucune catégorie définie.
    """
    cog = TopQS(bot)

    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "🃏 Yu-Gi-Oh!"

    await bot.add_cog(cog)
