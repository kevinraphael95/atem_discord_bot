# ────────────────────────────────────────────────────────────────────────────────
# 📌 quizzvocabulaire.py
# Objectif : Quiz interactif sur le vocabulaire Yu-Gi-Oh! (définition + choix)
#            Mode solo (seul l'auteur peut répondre) ou multi (premier qui clique gagne)
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 5 secondes par utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import random
from typing import List, Optional
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON (vocabulaire)
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "vocabulaire.json")

def load_vocabulaire():
    """Charge le fichier JSON contenant les termes du vocabulaire."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {DATA_JSON_PATH} : {e}")
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton de réponse
# ────────────────────────────────────────────────────────────────────────────────
class AnswerButton(Button):
    def __init__(self, label: str, correct_answer: str, parent_view: "QuizView"):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.correct_answer = correct_answer
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if self.parent_view.answered:
            await interaction.response.defer()
            return

        if self.parent_view.mode == "solo" and interaction.user.id != self.parent_view.author_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ton quiz !", ephemeral=True
            )
            return

        self.parent_view.answered = True
        self.parent_view.reveal_colors(chosen_label=self.label)

        embed = self.parent_view.base_embed.copy()
        if self.label == self.correct_answer:
            embed.add_field(
                name="Résultat",
                value=f"✅ {interaction.user.mention} a trouvé ! La bonne réponse était **{self.correct_answer}**.",
                inline=False
            )
        else:
            embed.add_field(
                name="Résultat",
                value=f"❌ {interaction.user.mention} s'est trompé. La bonne réponse était **{self.correct_answer}**.",
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=self.parent_view)
        self.parent_view.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue du quiz
# ────────────────────────────────────────────────────────────────────────────────
class QuizView(View):
    def __init__(self, cog, channel_id: int, base_embed: discord.Embed, options_list: List[str],
                 correct_answer: str, mode: str, author_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.channel_id = channel_id
        self.base_embed = base_embed
        self.correct_answer = correct_answer
        self.mode = mode  # "solo" ou "multi"
        self.author_id = author_id
        self.answered = False
        self.message: Optional[discord.Message] = None
        for opt in options_list:
            self.add_item(AnswerButton(label=opt, correct_answer=correct_answer, parent_view=self))

    def reveal_colors(self, chosen_label: str):
        """Colore le bouton correct en vert, le bouton choisi (si faux) en rouge, désactive tout."""
        for item in self.children:
            item.disabled = True
            if item.label == self.correct_answer:
                item.style = discord.ButtonStyle.success
            elif item.label == chosen_label:
                item.style = discord.ButtonStyle.danger

    async def on_timeout(self):
        if self.answered:
            return
        self.answered = True
        for item in self.children:
            item.disabled = True
            if item.label == self.correct_answer:
                item.style = discord.ButtonStyle.success
        self.cog.active_channels.discard(self.channel_id)
        if self.message:
            embed = self.base_embed.copy()
            embed.add_field(
                name="Résultat",
                value=f"⏰ Temps écoulé ! La bonne réponse était **{self.correct_answer}**.",
                inline=False
            )
            await safe_edit(self.message, embed=embed, view=self)

    def stop(self):
        self.cog.active_channels.discard(self.channel_id)
        super().stop()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec commandes prefix et slash
# ────────────────────────────────────────────────────────────────────────────────
class QuizzVocabulaire(commands.Cog):
    """Commande !quizzvocabulaire et /quizzvocabulaire — Quiz interactif sur le vocabulaire Yu-Gi-Oh!"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.vocabulaire = load_vocabulaire()
        self.active_channels = set()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour lancer le quiz
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_quiz(self, channel: discord.abc.Messageable, author: discord.abc.User, mode: str):
        if channel.id in self.active_channels:
            await safe_send(channel, "❌ Un quiz est déjà en cours dans ce salon.")
            return

        try:
            if len(self.vocabulaire) < 4:
                raise ValueError("Pas assez de données pour lancer un quiz.")

            terme, infos = random.choice(list(self.vocabulaire.items()))
            definition = infos.get("definition", "Définition indisponible.")

            autres_termes = [k for k in self.vocabulaire.keys() if k != terme]
            choix = random.sample(autres_termes, k=3)
            choix.append(terme)
            random.shuffle(choix)

            mode_label = "🔒 Solo" if mode == "solo" else "🌐 Multi (premier qui clique gagne)"
            embed = discord.Embed(
                title="📘 Quizz Vocabulaire Yu-Gi-Oh!",
                description=f"**Définition :**\n{definition}\n\nClique sur le bon terme :",
                color=discord.Color.dark_orange()
            )
            embed.set_footer(text=mode_label)

            view = QuizView(self, channel.id, embed, choix, terme, mode, author.id)
            self.active_channels.add(channel.id)
            view.message = await safe_send(channel, embed=embed, view=view)

        except Exception as e:
            self.active_channels.discard(channel.id)
            print(f"[ERREUR quizzvocabulaire] {e}")
            await safe_send(channel, f"❌ Une erreur est survenue : `{e}`")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="ygoquizzvocabulaire",
        aliases=["yqv", "ygoqv"],
        help="Lance un quiz de vocabulaire Yu-Gi-Oh!. Usage: !yqv [solo|multi] (solo par défaut)"
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_quizzvocabulaire(self, ctx: commands.Context, mode: str = "solo"):
        mode = mode.lower().strip()
        if mode not in ("solo", "multi"):
            mode = "solo"
        await self._start_quiz(ctx.channel, ctx.author, mode)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="ygoquizzvocabulaire", description="Fais un quiz interactif sur le vocabulaire Yu-Gi-Oh!")
    @app_commands.describe(mode="Solo (toi seul réponds) ou Multi (premier qui clique gagne)")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Solo", value="solo"),
        app_commands.Choice(name="Multi", value="multi"),
    ])
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_quizzvocabulaire(self, interaction: discord.Interaction, mode: Optional[app_commands.Choice[str]] = None):
        await interaction.response.defer()
        chosen_mode = mode.value if mode else "solo"
        await self._start_quiz(interaction.channel, interaction.user, chosen_mode)
        await interaction.delete_original_response()

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = QuizzVocabulaire(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
