# ────────────────────────────────────────────────────────────────────────────────
# 📌 mtgpendu.py
# Objectif :
#   - Jeu du pendu interactif avec cartes Magic: The Gathering
#   - Affiche type, couleur et set comme indice
#   - Tout caractère non alphabétique (espace, tiret, apostrophe, virgule, etc.)
#     est révélé automatiquement et ne compte pas comme une lettre à deviner
#   - Les accents sont ignorés
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 1 utilisation / 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import random
import unicodedata

from utils.discord_utils import safe_send, safe_edit, safe_delete

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Constantes Scryfall
# ────────────────────────────────────────────────────────────────────────────────
SCRYFALL_API = "https://api.scryfall.com"
HEADERS = {"User-Agent": "VaactMagicBot/1.0", "Accept": "application/json"}

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Constantes Pendu
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
INACTIVITE_MAX = 180  # 3 minutes

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Fonctions utilitaires
# ────────────────────────────────────────────────────────────────────────────────

# Ligatures et caractères précomposés que NFKD ne décompose pas en lettres simples.
# On les normalise manuellement avant la décomposition Unicode classique.
LIGATURES = {
    "æ": "ae", "Æ": "ae",
    "œ": "oe", "Œ": "oe",
    "ß": "ss",
}

def normaliser_texte(texte: str) -> str:
    """Supprime les accents, déplie les ligatures et met en minuscules."""
    for src, repl in LIGATURES.items():
        texte = texte.replace(src, repl)
    nfkd = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classes internes
# ────────────────────────────────────────────────────────────────────────────────
class PenduGame:
    def __init__(self, mot: str, mot_affiche: str, indice: str = None):
        self.mot = mot
        self.mot_affiche = mot_affiche
        self.indice = indice
        self.trouve = set()
        self.rate = set()
        self.terminee = False
        self.max_erreurs = MAX_ERREURS

    def get_display_word(self) -> str:
        """Affiche le mot : toute lettre non trouvée est masquée, tout caractère
        non alphabétique (espace, tiret, apostrophe, virgule, chiffre, etc.)
        est toujours visible."""
        res = ""
        for c in self.mot_affiche:
            if not c.isalpha():
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
            title="🕹️ Jeu du Pendu — cartes MTG",
            description=f"```\n{self.get_pendu_ascii()}\n```",
            color=discord.Color.purple()
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

class PenduSession:
    def __init__(self, game: PenduGame, message: discord.Message, author_id: int = None):
        self.game = game
        self.message = message
        self.last_activity = asyncio.get_event_loop().time()
        self.player_id = author_id

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MTGPendu(commands.Cog):
    """
    Commande /mtgpendu et !mtgpendu — Jeu du pendu interactif avec cartes MTG
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = {}
        self.verif_inactivite.start()

    def cog_unload(self):
        """Stoppe proprement la tâche de fond quand le cog est déchargé/rechargé,
        pour éviter d'avoir plusieurs boucles qui tournent en parallèle."""
        self.verif_inactivite.cancel()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Tirage aléatoire d'un mot
    # ────────────────────────────────────────────────────────────────────────────
    async def _fetch_random_word(self):
        try:
            session = self.bot.aiohttp_session
            async with session.get(f"{SCRYFALL_API}/cards/random", headers=HEADERS) as resp:
                if resp.status != 200:
                    raise ValueError("Carte introuvable")
                data = await resp.json()
                nom = data.get("name", "").strip()
                couleur = ", ".join(data.get("colors", [])) or "Incolore"
                type_line = data.get("type_line", "Inconnu")
                set_name = data.get("set_name", "Inconnu")
                indice = f"{type_line} / {couleur} / {set_name}"
                mot_normalise = normaliser_texte(nom)
                if len(mot_normalise) < 3:
                    raise ValueError("Nom trop court")
                return nom, mot_normalise, indice
        except Exception:
            fallback = [
                ("Black Lotus", "black lotus", "Artefact / Incolore / Alpha"),
                ("Lightning Bolt", "lightning bolt", "Éphémère / Rouge / Alpha"),
                ("Counterspell", "counterspell", "Contre / Bleu / Alpha"),
            ]
            return random.choice(fallback)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Démarrage de la partie
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_game(self, channel: discord.TextChannel, author):
        if channel.id in self.sessions:
            await safe_send(channel, "❌ Une partie est déjà en cours dans ce salon.")
            return
        mot_affiche, mot_normalise, indice = await self._fetch_random_word()
        game = PenduGame(mot_normalise, mot_affiche, indice=indice)
        message = await safe_send(channel, embed=game.create_embed())
        self.sessions[channel.id] = PenduSession(game, message, author_id=author.id)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="mtgpendu", description="Démarre une partie du jeu du pendu avec cartes MTG.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mtgpendu(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_game(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mtgpendu", help="Démarre une partie du jeu du pendu avec cartes MTG.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mtgpendu(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Gestion des lettres proposées
    # ────────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        session = self.sessions.get(message.channel.id)
        if not session:
            return
        if message.author.id != session.player_id:
            return
        contenu = message.content.strip().lower()
        if len(contenu) != 1 or not contenu.isalpha():
            return
        session.last_activity = asyncio.get_event_loop().time()
        game = session.game
        resultat = game.propose_lettre(contenu)
        if resultat is None:
            await safe_send(message.channel, f"❌ Lettre `{contenu}` déjà proposée.", delete_after=5)
            await safe_delete(message)
            return
        await safe_edit(session.message, embed=game.create_embed())
        await safe_delete(message)
        if resultat == "gagne":
            await safe_send(message.channel, f"🎉 Bravo {message.author.mention} ! Le mot était **{game.mot_affiche}**.")
            del self.sessions[message.channel.id]
        elif resultat == "perdu":
            await safe_send(message.channel, f"💀 Partie terminée ! Le mot était **{game.mot_affiche}**.")
            del self.sessions[message.channel.id]

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Vérification inactivité
    # ────────────────────────────────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def verif_inactivite(self):
        now = asyncio.get_event_loop().time()
        to_remove = [cid for cid, s in self.sessions.items() if now - s.last_activity > INACTIVITE_MAX]
        for cid in to_remove:
            session = self.sessions.pop(cid, None)
            if session:
                await safe_send(session.message.channel, "⏰ Partie terminée pour inactivité (3 minutes).")

    @verif_inactivite.before_loop
    async def before_verif_inactivite(self):
        await self.bot.wait_until_ready()

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MTGPendu(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
