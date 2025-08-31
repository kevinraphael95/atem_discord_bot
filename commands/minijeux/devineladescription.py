# ────────────────────────────────────────────────────────────────────────────────
# 📌 testquestion.py — Commande interactive !testquestion
# Objectif : Deviner une carte Yu-Gi-Oh à partir de sa description
# Catégorie : Minijeux
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import asyncio
import random
import re
from difflib import SequenceMatcher

from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_reply  # ✅ Utilisation des safe_

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Constantes
# ────────────────────────────────────────────────────────────────────────────────
REACTIONS = ["🇦", "🇧", "🇨", "🇩"]

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
        "@Ignister", "abc -", "abc-", "abyss", "ancient gear", "altergeist", "beetrouper", "branded", "cloudian", 
        "crusadia", "cyber", "D.D.", "dark magician", "dark world", "dinowrestler", 
        "dragonmaid", "dragon ruler", "dragunity", "exosister", "eyes of blue", "f.a", "f.a.", 
        "floowandereeze", "fur hire", "harpie", 
        "hero", "hurricail", "infinitrack", "kaiser", "kozaky", "labrynth", "live☆twin", "lunar light", "madolche", "marincess",
        "Mekk-Knight", "metalfoes", "naturia", "noble knight", "number", "numero", "numéro", 
        "oni", "Performapal", "phantasm spiral", "pot", "prophecy", "psychic", "punk", "rescue", "rose dragon", 
        "salamangreat", "sky striker", "tierra", "tri-brigade", "unchained"
    ]
    name = card.get("name", "").lower()
    return all(kw not in name for kw in banned_keywords)

def get_type_group(card_type):
    t = card_type.lower()
    if "monstre" in t: return "monstre"
    if "magie" in t:   return "magie"
    if "piège" in t:   return "piège"
    return "autre"

def censor_card_name(desc, name):
    return re.sub(re.escape(name), "[cette carte]", desc, flags=re.IGNORECASE)

# ────────────────────────────────────────────────────────────────────────────────
# 🔗 Requêtes API YGO
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_cards(limit=100):
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return random.sample(data.get("data", []), min(limit, len(data.get("data", []))))

async def fetch_archetype_cards(archetype):
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("data", [])

# ────────────────────────────────────────────────────────────────────────────────
# 🔄 Mise à jour des streaks
# ────────────────────────────────────────────────────────────────────────────────
async def update_streak(user_id: str, correct: bool):
    row = supabase.table("ygo_streaks").select("*").eq("user_id", user_id).execute().data
    current = row[0]["current_streak"] if row else 0
    best    = row[0].get("best_streak", 0) if row else 0
    new_streak = current + 1 if correct else 0
    new_best   = max(best, new_streak)
    payload = {
        "user_id": user_id,
        "current_streak": new_streak,
        "best_streak": new_best
    }
    if row:
        supabase.table("ygo_streaks").update(payload).eq("user_id", user_id).execute()
    else:
        supabase.table("ygo_streaks").insert(payload).execute()

# ────────────────────────────────────────────────────────────────────────────────
# 🧐 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TestQuestion(commands.Cog):
    """
    Commande !testquestion — Devinez une carte Yu-Gi-Oh! à partir de sa description. (multijoueur)
    """

    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}  # guild_id → message en cours

    # ────────────────────────────────────────────────────────────────────────────
    # 💬 COMMANDE : !testquestion (quiz)
    # ────────────────────────────────────────────────────────────────────────────
    @commands.group(
        name="devineladescription",
        aliases=["devinedescription", "dd"],
        help="Devinez la carte avec sa description (multijoueur)",
        invoke_without_command=True
    )
    @no_dm()
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def testquestion(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        if self.active_sessions.get(guild_id):
            return await safe_reply(ctx, "⚠️ Un quiz est déjà en cours.", mention_author=False)

        self.active_sessions[guild_id] = True

        try:
            cards = await fetch_cards()
            main_card = next((c for c in cards if "desc" in c and is_clean_card(c)), None)
            if not main_card:
                self.active_sessions[guild_id] = None
                return await safe_send(ctx, "❌ Aucune carte valide trouvée.")

            archetype = main_card.get("archetype")
            main_name = main_card["name"]
            main_desc = censor_card_name(main_card["desc"], main_name)
            main_type = main_card.get("type", "")
            type_group = get_type_group(main_type)

            if archetype:
                group = await fetch_archetype_cards(archetype)
                group = [c for c in group if c.get("name") != main_name and "desc" in c]
            else:
                group = [
                    c for c in cards
                    if c.get("name") != main_name
                    and "desc" in c
                    and get_type_group(c.get("type", "")) == type_group
                    and is_clean_card(c)
                ]
                group.sort(key=lambda c: common_word_score(main_name, c["name"]) 
                                    + similarity_ratio(main_name, c["name"]), reverse=True)

            if len(group) < 3:
                self.active_sessions[guild_id] = None
                return await safe_send(ctx, "❌ Pas assez de fausses cartes valides.")

            wrongs = random.sample(group, 3)
            choices = [main_name] + [c["name"] for c in wrongs]
            random.shuffle(choices)

            # Création de l'embed du quiz
            embed = discord.Embed(
                title="🧠 Quelle est cette carte ?",
                description=(
                    f"📘 **Type :** {main_type}\n"
                    f"📝 *{main_desc[:1500]}{'...' if len(main_desc) > 1500 else ''}*"
                ),
                color=discord.Color.purple()
            )
            embed.add_field(name="🔹 Archétype", value=f"||{archetype or 'Aucun'}||", inline=False)

            if main_type.lower().startswith("monstre"):
                embed.add_field(name="💥 ATK", value=str(main_card.get("atk", "—")), inline=True)
                embed.add_field(name="🛡️ DEF", value=str(main_card.get("def", "—")), inline=True)
                embed.add_field(name="⚙️ Niveau", value=str(main_card.get("level", "—")), inline=True)

            options_text = "\n".join(f"{REACTIONS[i]} – **{name}**" for i, name in enumerate(choices))
            embed.add_field(name="Choix", value=options_text, inline=False)

            quiz_msg = await safe_send(ctx, embed=embed)
            self.active_sessions[guild_id] = quiz_msg

            # Ajout des réactions
            for emoji in REACTIONS[:len(choices)]:
                try:
                    await quiz_msg.add_reaction(emoji)
                    await asyncio.sleep(0.4)
                except discord.HTTPException:
                    pass

            answers = {}
            winners = set()

            def check(reaction, user):
                return (
                    reaction.message.id == quiz_msg.id
                    and reaction.emoji in REACTIONS[:len(choices)]
                    and not user.bot
                    and user.id not in answers
                )

            # Collecte des réponses pendant 60s
            try:
                while True:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    idx = REACTIONS.index(reaction.emoji)
                    chosen = choices[idx]
                    answers[user.id] = chosen
                    if chosen == main_name:
                        winners.add(user)
                    await update_streak(str(user.id), chosen == main_name)
            except asyncio.TimeoutError:
                pass

            # Temps écoulé, affichage des résultats
            correct_emoji = REACTIONS[choices.index(main_name)]
            result_embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=(
                    f"✅ Réponse : {correct_emoji} **{main_name}**\n\n"
                    + (f"🎉 Gagnants : {', '.join(w.mention for w in winners)}"
                       if winners else "😢 Personne n'a trouvé...")
                ),
                color=discord.Color.green() if winners else discord.Color.red()
            )
            await safe_send(ctx, embed=result_embed)

        except Exception as e:
            await safe_send(ctx, f"❌ Erreur : `{e}`")
        finally:
            self.active_sessions[guild_id] = None

    # ────────────────────────────────────────────────────────────────────────────
    # 📊 SOUS-COMMANDE : !testquestion score
    # ────────────────────────────────────────────────────────────────────────────
    @testquestion.command(name="score", aliases=["streak", "s"])
    async def testquestion_score(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        try:
            resp = supabase.table("ygo_streaks")\
                           .select("current_streak,best_streak")\
                           .eq("user_id", user_id)\
                           .execute()
            if resp.data:
                cur = resp.data[0].get("current_streak", 0)
                best = resp.data[0].get("best_streak", 0)
                embed = discord.Embed(
                    title=f"🔥 Série de {ctx.author.display_name}",
                    color=discord.Color.blurple()
                )
                embed.add_field(name="Série actuelle", value=f"**{cur}**", inline=False)
                embed.add_field(name="Record absolu", value=f"**{best}**", inline=False)
                await safe_send(ctx, embed=embed)
            else:
                await safe_send(ctx,
                    embed=discord.Embed(
                        title="📉 Pas encore de série",
                        description="Lance `!testquestion` pour démarrer ta série !",
                        color=discord.Color.red()
                    )
                )
        except Exception as e:
            await safe_send(ctx, "🚨 Erreur lors de la récupération de ta série.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🏆 SOUS-COMMANDE : !testquestion top
    # ────────────────────────────────────────────────────────────────────────────
    @testquestion.command(name="top", aliases=["t"])
    async def testquestion_top(self, ctx: commands.Context):
        try:
            resp = supabase.table("ygo_streaks")\
                           .select("user_id,best_streak")\
                           .order("best_streak", desc=True)\
                           .limit(10)\
                           .execute()
            data = resp.data
            if not data:
                return await safe_send(ctx, "📉 Aucun streak enregistré.")
            lines = []
            for i, row in enumerate(data, start=1):
                uid = row["user_id"]
                best = row.get("best_streak", 0)
                user = await self.bot.fetch_user(int(uid)) if uid else None
                name = user.name if user else f"ID {uid}"
                medal = {1:"🥇",2:"🥈",3:"🥉"}.get(i, f"`#{i}`")
                lines.append(f"{medal} **{name}** – 🔥 {best}")
            embed = discord.Embed(
                title="🏆 Top 10 Séries",
                description="\n".join(lines),
                color=discord.Color.gold()
            )
            await safe_send(ctx, embed=embed)
        except Exception as e:
            await safe_send(ctx, "🚨 Erreur lors du classement.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestQuestion(bot)
    for command in cog.get_commands():
        command.category = "Minijeux"
    await bot.add_cog(cog)
