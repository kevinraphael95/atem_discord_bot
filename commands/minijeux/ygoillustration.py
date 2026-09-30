# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygoillustration.py
# Objectif : Deviner une carte Yu-Gi-Oh! à partir de son illustration croppée
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Version optimisée : 2 appels API par partie (0 cache, 0 RAM)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import random
import traceback

from utils.discord_utils import safe_send, safe_edit
from utils.card_utils import fetch_random_card, fetch_cards_by_type, fetch_cards_by_archetype

# ────────────────────────────────────────────────────────────────────────────────
# 🔒 Empêcher l'utilisation en MP
# ────────────────────────────────────────────────────────────────────────────────
def no_dm():
    async def predicate(ctx):
        if ctx.guild is None:
            await safe_send(ctx, "❌ Cette commande ne peut pas être utilisée en MP.")
            return False
        return True
    return commands.check(predicate)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — YGOIllustration
# ────────────────────────────────────────────────────────────────────────────────
class YGOIllustration(commands.Cog):
    """
    Commande /ygoillu et !ygoillu — Devine une carte Yu-Gi-Oh! à partir de son illustration croppée
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_sessions = {}

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Lancer le quiz
    # ────────────────────────────────────────────────────────────────────────────
    async def start_quiz(self, channel: discord.abc.Messageable):
        guild_id = getattr(channel, "guild", None).id if hasattr(channel, "guild") else None
        if guild_id and self.active_sessions.get(guild_id):
            return await safe_send(channel, "⚠️ Un quiz est déjà en cours.")
        if guild_id:
            self.active_sessions[guild_id] = True

        try:
            session = getattr(self.bot, "aiohttp_session", None)
            if not session or session.closed:
                return await safe_send(channel, "🚨 Session HTTP non disponible.")

            # 1️⃣ Carte à deviner (1 appel API)
            true_card, _ = await fetch_random_card(session)
            if not true_card:
                return await safe_send(channel, "🚨 Impossible de récupérer une carte.")

            image_url = true_card.get("card_images", [{}])[0].get("image_url_cropped")
            if not image_url:
                return await safe_send(channel, "🚫 Carte sans image croppée.")

            # 2️⃣ Cartes similaires (1 appel API)
            archetype = true_card.get("archetype")
            card_type = true_card.get("type", "")

            if archetype:
                similar = await fetch_cards_by_archetype(session, archetype, n=10)
            else:
                similar = await fetch_cards_by_type(session, card_type, n=10)

            # Filtre : retire la vraie carte + garde 3
            similar = [c for c in similar if c["name"] != true_card["name"]]
            similar = random.sample(similar, k=min(3, len(similar))) if similar else []

            if len(similar) < 3:
                return await safe_send(channel, "❌ Pas assez de cartes similaires.")

            # 3️⃣ Choix mélangés
            choices = [true_card["name"]] + [c["name"] for c in similar]
            random.shuffle(choices)
            correct_idx = choices.index(true_card["name"])

            # 4️⃣ Embed + View
            embed = discord.Embed(title="🖼️ Devine la carte !", color=discord.Color.purple())
            embed.set_image(url=image_url)
            embed.set_footer(text=f"🔹 Archétype : ||{true_card.get('archetype','Aucun')}||")

            view = self.QuizView(self.bot, choices, correct_idx)
            view.message = await safe_send(channel, embed=embed, view=view)
            await view.wait()

            # 5️⃣ Résultats
            winners = [self.bot.get_user(uid) for uid, idx in view.answers.items() if idx == correct_idx]

            result_embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=(
                    f"✅ Réponse : **{true_card['name']}**\n" +
                    (f"🎉 Gagnants : {', '.join(w.mention for w in winners if w)}"
                     if winners else "😢 Personne n'a trouvé...")
                ),
                color=discord.Color.green() if winners else discord.Color.red()
            )
            await safe_send(channel, embed=result_embed)

        except Exception as e:
            traceback.print_exc()
            await safe_send(channel, f"❌ Une erreur est survenue : {e}")
        finally:
            if guild_id:
                self.active_sessions[guild_id] = None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 View et Button pour le quiz
    # ────────────────────────────────────────────────────────────────────────────
    class QuizView(View):
        def __init__(self, bot, choices, correct_idx):
            super().__init__(timeout=60)
            self.bot = bot
            self.choices = choices
            self.correct_idx = correct_idx
            self.answers = {}
            for i, choice in enumerate(choices):
                self.add_item(YGOIllustration.QuizButton(label=choice, idx=i, parent_view=self))

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            if hasattr(self, "message"):
                await safe_edit(self.message, view=self)

    class QuizButton(Button):
        def __init__(self, label, idx, parent_view):
            super().__init__(label=label, style=discord.ButtonStyle.primary)
            self.parent_view = parent_view
            self.idx = idx

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id not in self.parent_view.answers:
                self.parent_view.answers[interaction.user.id] = self.idx
            await interaction.response.send_message(f"✅ Réponse enregistrée : **{self.label}**", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="ygoillustration", aliases=["ygoillu","yi"], help="Devine une carte Yu-Gi-Oh! à partir de son illustration")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @no_dm()
    async def prefix_ygoillu(self, ctx):
        await self.start_quiz(ctx.channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="ygoillustration", description="Devine une carte Yu-Gi-Oh! à partir de son illustration")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_ygoillu(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.start_quiz(interaction.channel)
        await interaction.delete_original_response()

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGOIllustration(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
