# ────────────────────────────────────────────────────────────────────────────────
# 📌 pendu.py — Commande interactive !pendu
# Objectif :
#   - Jeu du pendu interactif avec noms de cartes Yu-Gi-Oh! françaises
#   - Affiche type, attribut et archétype comme indice
#   - Les espaces, tirets et apostrophes ne comptent pas comme lettres
#   - Les accents sont ignorés (é/è/ê = e, ç = c, etc.)
# Catégorie : Minijeux
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import random
import unicodedata
from utils.discord_utils import safe_send, safe_edit
from utils.card_utils import fetch_random_card

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
INACTIVITE_MAX = 180  # ⏰ 3 minutes

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Fonction utilitaire : normaliser les lettres
# ────────────────────────────────────────────────────────────────────────────────
def normaliser_texte(texte: str) -> str:
    """Supprime les accents et met en minuscules"""
    nfkd = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classe PenduGame
# ────────────────────────────────────────────────────────────────────────────────
class PenduGame:
    def __init__(self, mot: str, mot_affiche: str, indice: str = None, mode: str = "solo"):
        self.mot = mot
        self.mot_affiche = mot_affiche
        self.indice = indice
        self.trouve = set()
        self.rate = set()
        self.terminee = False
        self.mode = mode
        self.max_erreurs = MAX_ERREURS

    def get_display_word(self) -> str:
        res = ""
        for c in self.mot_affiche:
            if c.lower() in (" ", "-", "'"):
                res += c
            else:
                c_norm = normaliser_texte(c)
                res += c if c_norm in self.trouve else "★"
        return res

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
        lettre = normaliser_texte(lettre)
        if lettre in self.trouve or lettre in self.rate:
            return None
        if lettre in self.mot:
            self.trouve.add(lettre)
        else:
            self.rate.add(lettre)

        if {c for c in self.mot if c.isalpha()}.issubset(self.trouve):
            self.terminee = True
            return "gagne"
        if len(self.rate) >= self.max_erreurs:
            self.terminee = True
            return "perdu"
        return "continue"

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classe PenduSession
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
        mode = "multi" if mode.lower() in ("multi", "m") else "solo"
        if ctx.channel.id in self.sessions:
            await safe_send(ctx.channel, "❌ Une partie est déjà en cours dans ce salon.")
            return

        mot_affiche, mot_normalise, indice = await self._fetch_random_word()
        if not mot_affiche:
            await safe_send(ctx.channel, "❌ Impossible de récupérer un mot, réessaie plus tard.")
            return

        game = PenduGame(mot_normalise, mot_affiche, indice=indice, mode=mode)
        message = await safe_send(ctx.channel, embed=game.create_embed())
        self.sessions[ctx.channel.id] = PenduSession(game, message, mode=mode, author_id=ctx.author.id)

    async def _fetch_random_word(self) -> tuple[str | None, str | None, str | None]:
        """Tire le nom d'une carte Yu-Gi-Oh! (FR) avec indice type/attribut/archétype"""
        try:
            carte, langue = await fetch_random_card(lang="fr")
            if not carte:
                raise ValueError("Carte introuvable")
            nom = carte.get("name", "").strip()
            type_raw = carte.get("type", "Inconnu")
            attr = carte.get("attribute", None)
            archetype = carte.get("archetype", None)
            indice = type_raw
            if attr:
                indice += f" / {attr}"
            if archetype:
                indice += f" / {archetype}"

            mot_normalise = normaliser_texte(nom)
            if len(mot_normalise) < 3:
                raise ValueError("Nom trop court")
            return nom, mot_normalise, indice
        except Exception as e:
            print(f"[ERREUR] _fetch_random_word : {e}")
            fallback = [
                ("Dragon Blanc aux Yeux Bleus", "dragon blanc aux yeux bleus", "Monstre / LUMIÈRE"),
                ("Magicien Sombre", "magicien sombre", "Magicien / TÉNÈBRES"),
                ("Kuriboh", "kuriboh", "Monstre / TÉNÈBRES"),
                ("Pot de Cupidité", "pot de cupidite", "Magie"),
                ("Force de Miroir", "force de miroir", "Piège"),
            ]
            return random.choice(fallback)

    @tasks.loop(seconds=30)
    async def verif_inactivite(self):
        now = asyncio.get_event_loop().time()
        a_supprimer = [cid for cid, s in self.sessions.items() if now - s.last_activity > INACTIVITE_MAX]
        for cid in a_supprimer:
            session = self.sessions.pop(cid, None)
            if session:
                await safe_send(session.message.channel, "⏰ Partie terminée pour inactivité (3 minutes).")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        session = self.sessions.get(message.channel.id)
        if not session:
            return
        if session.mode == "solo" and message.author.id != session.player_id:
            return

        contenu = message.content.strip().lower()
        if len(contenu) != 1 or not contenu.isalpha():
            return

        session.last_activity = asyncio.get_event_loop().time()
        game = session.game
        resultat = game.propose_lettre(contenu)

        if resultat is None:
            await safe_send(message.channel, f"❌ Lettre `{contenu}` déjà proposée.", delete_after=5)
            await message.delete()
            return

        await safe_edit(session.message, embed=game.create_embed())
        await message.delete()

        if resultat == "gagne":
            await safe_send(message.channel, f"🎉 Bravo {message.author.mention} ! Le mot était **{game.mot_affiche}**.")
            del self.sessions[message.channel.id]
        elif resultat == "perdu":
            await safe_send(message.channel, f"💀 Partie terminée ! Le mot était **{game.mot_affiche}**.")
            del self.sessions[message.channel.id]

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Pendu(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
