# ────────────────────────────────────────────────────────────────────────────────
# 📌 pendu.py — Commande interactive !pendu
# Objectif :
#   - Jeu du pendu interactif avec noms de cartes Yu-Gi-Oh! françaises
#   - Les espaces ne comptent pas comme lettres
# Catégorie : Jeux
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from utils.discord_utils import safe_send, safe_edit, safe_respond  # ✅ Utilisation safe_#
from utils.card_utils import fetch_random_card  # 🔹 Tirer une carte aléatoire

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Constantes et ASCII
# ────────────────────────────────────────────────────────────────────────────────
PENDU_ASCII = [
    "`     \n     \n     \n     \n     \n=========`",
    "`     +---+\n     |   |\n         |\n         |\n         |\n     =========`",
    "`     +---+\n     |   |\n     O   |\n         |\n         |\n     =========`",
    "`     +---+\n     |   |\n     O   |\n     |   |\n         |\n     =========`",
    "`     +---+\n     |   |\n     O   |\n    /|   |\n         |\n     =========`",
    "`     +---+\n     |   |\n     O   |\n    /|\\  |\n         |\n     =========`",
    "`     +---+\n     |   |\n     O   |\n    /|\\  |\n    /    |\n     =========`",
    "`     +---+\n     |   |\n     O   |\n    /|\\  |\n    / \\  |\n     =========`",
]

MAX_ERREURS = 7
INACTIVITE_MAX = 180  # ⏰ 3 minutes (en secondes)

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classe PenduGame
# ────────────────────────────────────────────────────────────────────────────────
class PenduGame:
    def __init__(self, mot: str, indice: str = None, mode: str = "solo"):
        self.mot = mot.lower()
        self.indice = indice  # 🔹 Indice facultatif
        self.trouve = set()
        self.rate = set()
        self.terminee = False
        self.mode = mode
        self.max_erreurs = min(len(mot) + 1, MAX_ERREURS)

    def get_display_word(self) -> str:
        """Affiche le mot avec _ pour les lettres non trouvées, espaces visibles"""
        return " ".join([l if (l in self.trouve or l == " ") else "_" for l in self.mot])

    def get_pendu_ascii(self) -> str:
        return PENDU_ASCII[min(len(self.rate), self.max_erreurs)]

    def get_lettres_tentees(self) -> str:
        lettres_tentees = sorted(self.trouve | self.rate)
        return ", ".join(lettres_tentees) if lettres_tentees else "Aucune"

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🕹️ Jeu du Pendu — mode {self.mode.capitalize()}",
            description=f"```\n{self.get_pendu_ascii()}\n```",
            color=discord.Color.blue()
        )
        embed.add_field(name="Mot", value=f"`{self.get_display_word()}`", inline=False)
        embed.add_field(name="Erreurs", value=f"`{len(self.rate)} / {self.max_erreurs}`", inline=False)
        embed.add_field(name="Lettres tentées", value=f"`{self.get_lettres_tentees()}`", inline=False)
        if self.indice:
            embed.add_field(name="Indice", value=f"`{self.indice}`", inline=False)
        embed.set_footer(text="✉️ Propose une lettre en répondant par un message contenant UNE lettre.")
        return embed

    def propose_lettre(self, lettre: str):
        lettre = lettre.lower()
        if lettre in self.trouve or lettre in self.rate:
            return None
        if lettre in self.mot:
            self.trouve.add(lettre)
        else:
            self.rate.add(lettre)

        # Vérifie si toutes les lettres (hors espaces) sont trouvées
        lettres_uniques = {l for l in self.mot if l.isalpha()}
        if lettres_uniques.issubset(self.trouve):
            self.terminee = True
            return "gagne"

        if len(self.rate) >= self.max_erreurs:
            self.terminee = True
            return "perdu"

        return "continue"

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classe PenduSession (pour solo et multi)
# ────────────────────────────────────────────────────────────────────────────────
class PenduSession:
    def __init__(self, game: PenduGame, message: discord.Message, mode: str = "solo", author_id: int = None):
        self.game = game
        self.message = message
        self.mode = mode
        self.last_activity = asyncio.get_event_loop().time()
        if mode == "multi":
            self.players = set()
        else:
            self.player_id = author_id

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Pendu(commands.Cog):
    """
    Commande !pendu — Jeu du pendu interactif avec noms de cartes Yu-Gi-Oh! françaises
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = {}
        self.http_session = aiohttp.ClientSession()
        self.verif_inactivite.start()

    def cog_unload(self):
        self.verif_inactivite.cancel()

    @commands.command(
        name="pendu",
        help="Démarre une partie du jeu du pendu avec cartes Yu-Gi-Oh! françaises.",
        description="Lance une partie, puis propose des lettres par message."
    )
    async def pendu_cmd(self, ctx: commands.Context, mode: str = ""):
        mode = mode.lower()
        if mode not in ("multi", "m"):
            mode = "solo"

        channel_id = ctx.channel.id
        if channel_id in self.sessions:
            await safe_send(ctx.channel, "❌ Une partie est déjà en cours dans ce salon.")
            return

        # 🔹 Récupération du mot et de l’indice
        mot, indice = await self._fetch_random_word()
        if not mot:
            await safe_send(ctx.channel, "❌ Impossible de récupérer un mot, réessaie plus tard.")
            return

        game = PenduGame(mot, indice=indice, mode=mode)
        embed = game.create_embed()
        message = await safe_send(ctx.channel, embed=embed)
        session = PenduSession(game, message, mode=mode, author_id=ctx.author.id)
        self.sessions[channel_id] = session

    # ───────────────────────────────────────────────────────────────────────
    async def _fetch_random_word(self) -> tuple[str | None, str | None]:
        """Tire aléatoirement le nom d'une carte Yu-Gi-Oh! française et génère un indice"""
        try:
            carte, langue = await fetch_random_card(lang="fr")  # ✅ Nom français
            if not carte:
                return None, None
            nom = carte.get("name", "").lower()
            type_raw = carte.get("type", "Inconnu")
            attr = carte.get("attribute", None)
            indice = type_raw
            if attr:
                indice += f" / {attr}"
            return nom if nom else None, indice
        except Exception:
            return None, None

    # ───────────────────────────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def verif_inactivite(self):
        now = asyncio.get_event_loop().time()
        a_supprimer = []
        for channel_id, session in list(self.sessions.items()):
            if now - session.last_activity > INACTIVITE_MAX:
                a_supprimer.append(channel_id)
        for cid in a_supprimer:
            session = self.sessions.pop(cid, None)
            if session:
                await safe_send(
                    session.message.channel,
                    "⏰ Partie terminée pour inactivité (3 minutes sans réponse)."
                )

    # ───────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        session: PenduSession = self.sessions.get(channel_id)
        if not session:
            return

        if session.mode == "solo" and message.author.id != session.player_id:
            return

        content = message.content.strip().lower()
        if len(content) != 1 or not content.isalpha():
            return

        session.last_activity = asyncio.get_event_loop().time()
        game = session.game
        resultat = game.propose_lettre(content)

        if resultat is None:
            await safe_send(message.channel, f"❌ Lettre `{content}` déjà proposée.", delete_after=5)
            await message.delete()
            return

        embed = game.create_embed()
        try:
            await safe_edit(session.message, embed=embed)
        except discord.NotFound:
            del self.sessions[channel_id]
            await safe_send(message.channel, "❌ Partie annulée car le message du jeu a été supprimé.")
            return

        await message.delete()

        if resultat == "gagne":
            await safe_send(message.channel, f"🎉 Bravo {message.author.mention}, le mot `{game.mot}` a été deviné !")
            del self.sessions[channel_id]
            return

        if resultat == "perdu":
            await safe_send(message.channel, f"💀 Partie terminée ! Le mot était `{game.mot}`.")
            del self.sessions[channel_id]
            return

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Pendu(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
