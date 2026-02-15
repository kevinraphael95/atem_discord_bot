# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygodescription.py
# Objectif : Deviner une carte Yu-Gi-Oh à partir de sa description
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 1 utilisation / 8 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import random
import re
import sqlite3
from difflib import SequenceMatcher
import aiohttp

from utils.discord_utils import safe_send, safe_reply, safe_edit
from utils.vaact_utils import add_exp_for_streak, DB_PATH

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
# 🔍 Fonctions utilitaires
# ────────────────────────────────────────────────────────────────────────────────
def similarity_ratio(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def common_word_score(a, b):
    return len(set(a.lower().split()) & set(b.lower().split()))

def is_clean_card(card):
    banned_keywords = [
        "@Ignister","abc","abyss","ancient gear","altergeist","beetrouper","branded",
        "cloudian","crusadia","cyber","D.D.","dark magician","dark world","dinowrestler",
        "dragonmaid","dragon ruler","dragunity","exosister","eyes of blue","f.a","floowandereeze",
        "fur hire","harpie","hero","hurricail","infinitrack","kaiser","kozaky","labrynth",
        "live☆twin","lunar light","madolche","marincess","Mekk-Knight","metalfoes","naturia",
        "noble knight","number","numero","numéro","oni","Performapal","phantasm spiral","pot",
        "prophecy","psychic","punk","rescue","rose dragon","salamangreat","sky striker",
        "tierra","tri-brigade","unchained"
    ]
    name = card.get("name","").lower()
    return all(kw not in name for kw in banned_keywords)

def get_type_group(card_type):
    t = card_type.lower()
    if "monstre" in t: return "monstre"
    if "magie" in t: return "magie"
    if "piège" in t: return "piège"
    return "autre"

def censor_card_name(desc, name):
    return re.sub(re.escape(name), "[cette carte]", desc, flags=re.IGNORECASE)

# ────────────────────────────────────────────────────────────────────────────────
# 🔄 Mise à jour des streaks et EXP (SQLite)
# ────────────────────────────────────────────────────────────────────────────────
async def update_streak(user_id: str, correct: bool):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT current_streak, best_streak FROM profil WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    current = row[0] if row else 0
    best = row[1] if row else 0
    new_streak = current + 1 if correct else 0
    new_best = max(best, new_streak)

    if row:
        cursor.execute("UPDATE profil SET current_streak=?, best_streak=? WHERE user_id=?",
                       (new_streak, new_best, user_id))
    else:
        cursor.execute(
            "INSERT INTO profil (user_id, username, cartefav, vaact_name, fav_decks_vaact, current_streak, best_streak) VALUES (?,?,?,?,?,?,?)",
            (user_id, f"ID {user_id}", "Non défini", "Non défini", "Non défini", new_streak, new_best)
        )
    conn.commit()
    conn.close()

    if new_best > best:
        await add_exp_for_streak(user_id, new_best)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View et boutons du quiz
# ────────────────────────────────────────────────────────────────────────────────
class QuizView(View):
    def __init__(self, bot, choices, main_name):
        super().__init__(timeout=60)
        self.bot = bot
        self.choices = choices
        self.main_name = main_name
        self.answers = {}
        for idx, name in enumerate(choices):
            self.add_item(QuizButton(label=name, idx=idx, parent_view=self))
        self.message = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class QuizButton(Button):
    def __init__(self, label, idx, parent_view):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
        self.idx = idx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id not in self.parent_view.answers:
            self.parent_view.answers[interaction.user.id] = self.idx
            await update_streak(
                str(interaction.user.id),
                self.parent_view.choices[self.idx] == self.parent_view.main_name
            )
        await interaction.response.send_message(
            f"✅ Réponse enregistrée : **{self.label}**",
            ephemeral=True
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class YGODescription(commands.Cog):
    """
    Commande /ygodescription et !ygodescription — Devine une carte Yu-Gi-Oh à partir de sa description
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_sessions = {}  # guild_id → quiz en cours

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_quiz(self, ctx_or_inter, interaction=False):
        guild_id = ctx_or_inter.guild.id
        if self.active_sessions.get(guild_id):
            return await safe_reply(ctx_or_inter,"⚠️ Un quiz est déjà en cours.", mention_author=False)
        self.active_sessions[guild_id] = True

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
                async with session.get(url) as resp:
                    data = await resp.json()
                    cards = random.sample(data.get("data", []), min(100, len(data.get("data", []))))

            main_card = next((c for c in cards if "desc" in c and is_clean_card(c)), None)
            if not main_card:
                return await safe_send(ctx_or_inter,"❌ Aucune carte valide trouvée.")

            main_name = main_card["name"]
            main_desc = censor_card_name(main_card["desc"], main_name)
            main_type = main_card.get("type","")
            archetype = main_card.get("archetype")
            type_group = get_type_group(main_type)

            if archetype:
                group = [c for c in cards if c.get("name") != main_name and "desc" in c]
            else:
                group = [c for c in cards if c.get("name") != main_name and "desc" in c and get_type_group(c.get("type",""))==type_group and is_clean_card(c)]
                group.sort(key=lambda c: common_word_score(main_name,c["name"])+similarity_ratio(main_name,c["name"]), reverse=True)

            if len(group) < 3:
                return await safe_send(ctx_or_inter,"❌ Pas assez de fausses cartes valides.")

            wrongs = random.sample(group,3)
            choices = [main_name]+[c["name"] for c in wrongs]
            random.shuffle(choices)

            embed = discord.Embed(
                title="🧠 Quelle est cette carte ?",
                description=f"📘 **Type :** {main_type}\n📝 *{main_desc[:1500]}{'...' if len(main_desc)>1500 else ''}*",
                color=discord.Color.purple()
            )
            embed.add_field(name="🔹 Archétype", value=f"||{archetype or 'Aucun'}||", inline=False)
            if main_type.lower().startswith("monstre"):
                embed.add_field(name="💥 ATK", value=str(main_card.get("atk","—")), inline=True)
                embed.add_field(name="🛡️ DEF", value=str(main_card.get("def","—")), inline=True)
                embed.add_field(name="⚙️ Niveau", value=str(main_card.get("level","—")), inline=True)

            view = QuizView(self.bot, choices, main_name)
            if interaction:
                view.message = await safe_send(ctx_or_inter.channel, embed=embed, view=view)
            else:
                view.message = await safe_send(ctx_or_inter, embed=embed, view=view)
            await view.wait()

            winners = [self.bot.get_user(uid) for uid, idx in view.answers.items() if choices[idx]==main_name]
            result_embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=(f"✅ Réponse : **{main_name}**\n"
                             + (f"🎉 Gagnants : {', '.join(w.mention for w in winners if w)}" if winners else "😢 Personne n'a trouvé...")),
                color=discord.Color.green() if winners else discord.Color.red()
            )
            await safe_send(ctx_or_inter, embed=result_embed)

        except Exception as e:
            await safe_send(ctx_or_inter, f"❌ Erreur : `{e}`")
        finally:
            self.active_sessions[guild_id] = None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ygodescription",
        description="Devine une carte Yu-Gi-Oh à partir de sa description"
    )
    @app_commands.checks.cooldown(rate=1, per=8.0, key=lambda i: i.user.id)
    async def slash_ygodescription(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_quiz(interaction, interaction=True)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="ygodescription",
        aliases=["ygodesc","yd"],
        help="Devine une carte Yu-Gi-Oh à partir de sa description"
    )
    @no_dm()
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def prefix_ygodescription(self, ctx):
        await self._start_quiz(ctx)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = YGODescription(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
