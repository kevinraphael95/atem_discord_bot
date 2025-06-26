# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi.py — Commande interactive !tournoi
# Objectif : Affiche la date du prochain tournoi à partir de Supabase + système de rappel
# Catégorie : 🧠 VAACT
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import os
from datetime import datetime
import locale

# ────────────────────────────────────────────────────────────────────────────────
# 🌍 Configuration régionale
# ────────────────────────────────────────────────────────────────────────────────
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')  # Unix/Linux/Mac
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR')  # Windows
    except locale.Error:
        pass  # fallback manuel plus bas

# ────────────────────────────────────────────────────────────────────────────────
# 🔐 Configuration Supabase
# ────────────────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SHEET_CSV_URL = os.getenv("SHEET_CSV_URL2")

# ────────────────────────────────────────────────────────────────────────────────
# 🔔 Emoji de rappel
# ────────────────────────────────────────────────────────────────────────────────
EMOJI_RAPPEL = "🛎️"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiCommand(commands.Cog):
    """
    Commande !tournoi — Affiche la date du prochain tournoi et permet aux utilisateurs
    de recevoir un rappel automatique via message privé.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="tournoi",
        help="📅 Affiche la date du prochain tournoi VAACT.",
        description="Récupère la date du tournoi depuis Supabase et permet de s’inscrire au rappel."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)  # 🧊 Anti-spam : 1 appel / 3s / utilisateur
    async def tournoi(self, ctx: commands.Context):
        """Commande principale !tournoi."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            await ctx.send("❌ Configuration manquante (SUPABASE_URL ou SUPABASE_KEY).")
            return

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{SUPABASE_URL}/rest/v1/tournoi_info?select=prochaine_date&order=id.desc&limit=1"
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        await ctx.send("❌ Erreur lors de la récupération des données Supabase.")
                        return
                    data = await response.json()
        except Exception as e:
            print(f"[ERREUR tournoi] {e}")
            await ctx.send("❌ Erreur de connexion à Supabase.")
            return

        if not data or not data[0].get("prochaine_date"):
            await ctx.send("📭 Aucun tournoi prévu pour le moment.")
            return

        # ─── Formatage de la date ────────────────────────────────────────────────
        iso_date = data[0]["prochaine_date"]
        try:
            dt_obj = datetime.fromisoformat(iso_date)
            date_formatee = dt_obj.strftime('%d %B %Y à %Hh%M')
        except Exception:
            date_formatee = iso_date  # fallback brut si parsing échoue

        # ─── Construction de l'embed ─────────────────────────────────────────────
        embed = discord.Embed(
            title="📅 Prochain tournoi",
            description=(
                f"📆 **Date du prochain tournoi VAACT** :\n"
                f"➡️ **{date_formatee}**\n\n"
                f"📋 **Decks libres et pris** :\n"
                f"[Clique ici pour voir la liste]({SHEET_CSV_URL})"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Réagis à ce message avec {EMOJI_RAPPEL} pour recevoir un rappel 3 jours avant. (pour l'instant ça marche pas)")

        message = await ctx.send(embed=embed)
        await message.add_reaction(EMOJI_RAPPEL)

        def check(reaction, user):
            return (
                reaction.message.id == message.id
                and str(reaction.emoji) == EMOJI_RAPPEL
                and not user.bot
            )

        # ─── Attente de réactions pendant 15 minutes ─────────────────────────────
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=900.0, check=check)

                async with aiohttp.ClientSession() as session:
                    # Vérifie si l’utilisateur est déjà inscrit
                    url = f"{SUPABASE_URL}/rest/v1/rappels_tournoi?user_id=eq.{user.id}"
                    headers["Prefer"] = "resolution=merge-duplicates"
                    async with session.get(url, headers=headers) as r:
                        exists = await r.json()

                    if exists:
                        try:
                            await user.send("🛎️ Tu es déjà inscrit pour recevoir un rappel 3 jours avant le tournoi !")
                        except discord.Forbidden:
                            await ctx.send(f"{user.mention}, je ne peux pas t’envoyer de message privé. Active-les.")
                        continue

                    # Sinon, inscription de l’utilisateur
                    async with session.post(
                        f"{SUPABASE_URL}/rest/v1/rappels_tournoi",
                        headers={**headers, "Content-Type": "application/json"},
                        json={"user_id": str(user.id)}
                    ) as insert_resp:
                        if insert_resp.status in [200, 201]:
                            try:
                                await user.send("✅ Tu recevras un rappel 3 jours avant le tournoi !")
                            except discord.Forbidden:
                                await ctx.send(f"{user.mention}, je ne peux pas t’envoyer de message privé. Active-les.")
                        else:
                            print("[SUPABASE INSERT ERROR]", await insert_resp.text())

            except Exception as e:
                print("[REACTION TIMEOUT OU ERREUR]", e)
                break

    def cog_load(self):
        self.tournoi.category = "VAACT"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
    print("✅ Cog chargé : TournoiCommand (catégorie = VAACT)")
