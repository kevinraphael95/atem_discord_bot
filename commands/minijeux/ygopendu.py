# ================================================================================
# 📌 pendu.py
# Objectif :
#    - Jeu du pendu interactif avec bouton "Répondre" (Modal) et mode Buzzer (Multi)
#    - Noms de cartes Yu-Gi-Oh! françaises avec indices (Type, Attribut, Archétype)
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 1 utilisation / 5s
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import random
import unicodedata

from utils.discord_utils import safe_send, safe_edit, safe_defer, safe_delete
from utils.card_utils import fetch_random_card

# ================================================================================
# 🎨 Constantes
# ================================================================================
PENDU_ASCII = [
    "`      \n      \n      \n      \n      \n=========`",
    "`      +---+\n      |   |\n          |\n          |\n          |\n=========`",
    "`      +---+\n      |   |\n      O   |\n          |\n          |\n=========`",
    "`      +---+\n      |   |\n      O   |\n      |   |\n          |\n=========`",
    "`      +---+\n      |   |\n      O   |\n     /|   |\n          |\n=========`",
    "`      +---+\n      |   |\n      O   |\n     /|\\  |\n          |\n=========`",
    "`      +---+\n      |   |\n      O   |\n     /|\\  |\n     /    |\n=========`",
    "`      +---+\n      |   |\n      O   |\n     /|\\  |\n     / \\  |\n=========`",
]

MAX_ERREURS = 7
INACTIVITE_MAX = 180  # 3 minutes

# ================================================================================
# 🧩 Fonctions utilitaires
# ================================================================================
def normaliser_texte(texte: str) -> str:
    """Supprime les accents et met en minuscules"""
    nfkd = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


# ================================================================================
# 📝 Modal pour saisir la lettre ou le mot
# ================================================================================
class PenduModal(discord.ui.Modal, title="Proposer une lettre ou un mot"):
    lettre = discord.ui.TextInput(
        label="Votre proposition",
        placeholder="Entrez une lettre (ex: A) ou le mot complet",
        max_length=50,
        required=True
    )

    def __init__(self, session):
        super().__init__()
        self.session = session

    async def on_submit(self, interaction: discord.Interaction):
        session = self.session
        game = session.game

        # Vérification des droits selon le mode
        if session.mode == "solo" and interaction.user.id != session.player_id:
            await interaction.response.send_message("❌ Tu ne participes pas à cette partie solo !", ephemeral=True)
            return
        if session.mode == "multi" and session.players and interaction.user.id not in session.players:
            await interaction.response.send_message("❌ Tu dois cliquer sur 'Buzzer / Rejoindre' avant de proposer !", ephemeral=True)
            return

        session.last_activity = asyncio.get_event_loop().time()
        contenu = self.lettre.value.strip().lower()

        # Cas 1 : Une seule lettre
        if len(contenu) == 1 and contenu.isalpha():
            resultat = game.propose_lettre(contenu)
            if resultat is None:
                await interaction.response.send_message(f"❌ Lettre `{contenu}` déjà proposée !", ephemeral=True)
                return
            await interaction.response.defer()

        # Cas 2 : Tentative de mot complet
        elif len(contenu) > 1:
            norm_saisi = normaliser_texte(contenu)
            norm_mot = normaliser_texte(game.mot)
            if norm_saisi == norm_mot:
                game.terminee = True
                resultat = "gagne"
                for c in game.mot:
                    if c.isalpha():
                        game.trouve.add(normaliser_texte(c))
            else:
                game.rate.add(f"mot:{contenu}")
                erreurs_actuelles = len([r for r in game.rate if not r.startswith("mot:")])
                if erreurs_actuelles >= game.max_erreurs:
                    game.terminee = True
                    resultat = "perdu"
                else:
                    resultat = "continue"
            await interaction.response.send_message(f"🔍 Proposition de mot complet `{contenu}` : **{'Gagné !' if resultat == 'gagne' else 'Raté !'}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Veuillez entrer une valeur valide.", ephemeral=True)
            return

        # Mise à jour de l'affichage
        view = session.view
        if game.terminee:
            for child in view.children:
                child.disabled = True

        await session.message.edit(embed=game.create_embed(), view=view)

        # Annonces de fin de partie
        if resultat == "gagne":
            await interaction.channel.send(f"🎉 Bravo {interaction.user.mention} ! Le mot était **{game.mot_affiche}**.")
            if interaction.channel.id in session.cog.sessions:
                del session.cog.sessions[interaction.channel.id]
        elif resultat == "perdu":
            await interaction.channel.send(f"💀 Partie terminée ! Le mot était **{game.mot_affiche}**.")
            if interaction.channel.id in session.cog.sessions:
                del session.cog.sessions[interaction.channel.id]


# ================================================================================
# 🎛️ Vue des boutons (Répondre / Buzzer)
# ================================================================================
class PenduView(discord.ui.View):
    def __init__(self, session):
        super().__init__(timeout=INACTIVITE_MAX)
        self.session = session

    @discord.ui.button(label="Proposer", style=discord.ButtonStyle.primary, emoji="✍️", custom_id="pendu_proposer")
    async def proposer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.session.mode == "solo" and interaction.user.id != self.session.player_id:
            await interaction.response.send_message("❌ Tu ne participes pas à cette partie solo !", ephemeral=True)
            return
        if self.session.mode == "multi" and self.session.players and interaction.user.id not in self.session.players:
            await interaction.response.send_message("❌ Clique d'abord sur 'Buzzer / Rejoindre' pour participer !", ephemeral=True)
            return
        await interaction.response.send_modal(PenduModal(self.session))

    @discord.ui.button(label="Buzzer / Rejoindre", style=discord.ButtonStyle.success, emoji="🔔", custom_id="pendu_buzzer")
    async def buzzer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = self.session
        if session.mode != "multi":
            await interaction.response.send_message("ℹ️ Cette partie est en mode Solo.", ephemeral=True)
            return
        
        if interaction.user.id not in session.players:
            session.players.add(interaction.user.id)
            await interaction.response.send_message(f"🔔 {interaction.user.mention} a rejoint la partie multijoueur !", ephemeral=False)
        else:
            await interaction.response.send_message("✅ Tu es déjà inscrit dans cette partie !", ephemeral=True)


# ================================================================================
# 🧩 Classes de jeu et Session
# ================================================================================
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
        erreurs_count = len([r for r in self.rate if not r.startswith("mot:")])
        return PENDU_ASCII[min(erreurs_count, self.max_erreurs)]

    def get_lettres_tentees(self) -> str:
        lettres_tentees = sorted([l.upper() for l in self.trouve | self.rate if not l.startswith("mot:")])
        return ", ".join(lettres_tentees) if lettres_tentees else "Aucune"

    def create_embed(self) -> discord.Embed:
        erreurs_count = len([r for r in self.rate if not r.startswith("mot:")])
        embed = discord.Embed(
            title=f"🕹️ Jeu du Pendu — mode {self.mode.capitalize()}",
            description=f"```\n{self.get_pendu_ascii()}\n```",
            color=discord.Color.blue()
        )
        embed.add_field(name="Mot", value=f"`{self.get_display_word()}`", inline=False)
        embed.add_field(name="Erreurs", value=f"`{erreurs_count} / {self.max_erreurs}`", inline=False)
        embed.add_field(name="Lettres tentées", value=f"`{self.get_lettres_tentees()}`", inline=False)
        if self.indice:
            embed.add_field(name="Indice", value=f"`{self.indice}`", inline=False)
        embed.set_footer(text="Clique sur 'Proposer' pour entrer une lettre ou un mot.")
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
        
        erreurs_count = len([r for r in self.rate if not r.startswith("mot:")])
        if erreurs_count >= self.max_erreurs:
            self.terminee = True
            return "perdu"
        return "continue"


class PenduSession:
    def __init__(self, game: PenduGame, message: discord.Message, view, cog, mode: str = "solo", author_id: int = None):
        self.game = game
        self.message = message
        self.view = view
        self.cog = cog
        self.mode = mode
        self.last_activity = asyncio.get_event_loop().time()
        self.player_id = author_id
        self.players = {author_id} if author_id and mode == "multi" else set()


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Pendu(commands.Cog):
    """Commande /pendu et !pendu — Jeu du pendu avec boutons et modal"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = {}
        self.verif_inactivite.start()

    def cog_unload(self):
        self.verif_inactivite.cancel()

    # ============================================================================
    # 🔹 Tirage aléatoire d'un mot
    # ============================================================================
    async def _fetch_random_word(self):
        try:
            carte, _ = await fetch_random_card(self.bot.aiohttp_session)
            if not carte:
                raise ValueError("Carte introuvable")

            nom = carte.get("name", "").strip()
            type_raw = carte.get("type", "Inconnu")
            attr = carte.get("attribute")
            archetype = carte.get("archetype")
            indice = type_raw
            if attr:
                indice += f" / {attr}"
            if archetype:
                indice += f" / {archetype}"

            mot_normalise = normaliser_texte(nom)
            if len(mot_normalise) < 3:
                raise ValueError("Nom trop court")

            return nom, mot_normalise, indice

        except Exception:
            fallback = [
                ("Dragon Blanc aux Yeux Bleus", "dragon blanc aux yeux bleus", "Monstre / LUMIÈRE"),
                ("Magicien Sombre", "magicien sombre", "Magicien / TÉNÈBRES"),
                ("Kuriboh", "kuriboh", "Monstre / TÉNÈBRES"),
                ("Pot de Cupidité", "pot de cupidite", "Magie"),
                ("Force de Miroir", "force de miroir", "Piège"),
            ]
            return random.choice(fallback)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="pendu", description="Démarre une partie du jeu du pendu avec cartes Yu-Gi-Oh! françaises.")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Solo", value="solo"),
        app_commands.Choice(name="Multi", value="multi")
    ])
    async def slash_pendu(self, interaction: discord.Interaction, mode: str = "solo"):
        if not await safe_defer(interaction):
            return
        await self._start_game(interaction.channel, interaction.user, mode)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="pendu", help="Démarre une partie du pendu. Utilisez 'multi' ou 'm' pour jouer à plusieurs.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_pendu(self, ctx: commands.Context, mode: str = "solo"):
        m = "multi" if mode.lower() in ("multi", "m") else "solo"
        await self._start_game(ctx.channel, ctx.author, m)

    # ============================================================================
    # 🔹 Démarrage de la partie
    # ============================================================================
    async def _start_game(self, channel: discord.TextChannel, author, mode: str):
        if channel.id in self.sessions:
            await safe_send(channel, "❌ Une partie est déjà en cours dans ce salon.")
            return
            
        mot_affiche, mot_normalise, indice = await self._fetch_random_word()
        game = PenduGame(mot_normalise, mot_affiche, indice=indice, mode=mode)
        
        session = PenduSession(game, None, None, self, mode=mode, author_id=author.id)
        view = PenduView(session)
        session.view = view
        
        message = await safe_send(channel, embed=game.create_embed(), view=view)
        session.message = message
        self.sessions[channel.id] = session

    # ============================================================================
    # 🔹 Vérification inactivité
    # ============================================================================
    @tasks.loop(seconds=30)
    async def verif_inactivite(self):
        now = asyncio.get_event_loop().time()
        to_remove = [cid for cid, s in self.sessions.items() if now - s.last_activity > INACTIVITE_MAX]
        for cid in to_remove:
            session = self.sessions.pop(cid, None)
            if session and session.message:
                try:
                    for child in session.view.children:
                        child.disabled = True
                    await session.message.edit(view=session.view)
                except Exception:
                    pass
                await safe_send(session.message.channel, "⏰ Partie terminée pour inactivité (3 minutes).")

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Pendu(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
