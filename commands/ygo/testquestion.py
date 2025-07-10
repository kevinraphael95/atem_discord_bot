# ─────────────────────────────────────────────────────────────────────────
# 📌 testquestion.py — Commande interactive !testquestion
# Objectif : Deviner une carte Yu-Gi-Oh à partir de sa description
# Catégorie : Yu-Gi-Oh
# Accès : Public
# ─────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────
# 📆 Imports nécessaires
# ──────────────────────────────────────────
import discord
from discord.ext import commands
import aiohttp
import asyncio
import random
import re
from difflib import SequenceMatcher
from supabase_client import supabase

# ─────────────────────────────────────────────────────────────────────────
# 🔹 Constantes
# ─────────────────────────────────────────────────────────────────────────
REACTIONS = ["🇦", "🇧", "🇨", "🇩"]

# ─────────────────────────────────────────────────────────────────────────
# 🔒 Empêcher l'utilisation en MP
# ─────────────────────────────────────────────────────────────────────────
def no_dm():
    async def predicate(ctx):
        if ctx.guild is None:
            await ctx.send("❌ Cette commande ne peut pas être utilisée en MP.")
            return False
        return True
    return commands.check(predicate)

# ─────────────────────────────────────────────────────────────────────────
# 🔍 Fonctions utilitaires
# ─────────────────────────────────────────────────────────────────────────
def similarity_ratio(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def common_word_score(a, b):
    return len(set(a.lower().split()) & set(b.lower().split()))

def is_clean_card(card):
    banned_keywords = ["hero", "dark magician", "branded", "traptrix", "zoodiac"]
    name = card.get("name", "").lower()
    return all(kw not in name for kw in banned_keywords)

def get_type_group(card_type):
    t = card_type.lower()
    if "monstre" in t: return "monstre"
    if "magie" in t: return "magie"
    if "piège" in t: return "piège"
    return "autre"

def censor_card_name(desc, name):
    return re.sub(re.escape(name), "[cette carte]", desc, flags=re.IGNORECASE)

# ─────────────────────────────────────────────────────────────────────────
# 🔗 Requêtes API YGO
# ─────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────
# 🔄 Mise à jour des streaks
# ─────────────────────────────────────────────────────────────────────────
async def update_streak(user_id: str, correct: bool):
    data = supabase.table("ygo_streaks").select("*").eq("user_id", user_id).execute()
    row = data.data[0] if data.data else None
    new_streak = (row["current_streak"] + 1 if correct else 0) if row else (1 if correct else 0)
    best = max(row.get("best_streak", 0), new_streak) if row else new_streak
    payload = {"user_id": user_id, "current_streak": new_streak, "best_streak": best}
    if row:
        supabase.table("ygo_streaks").update(payload).eq("user_id", user_id).execute()
    else:
        supabase.table("ygo_streaks").insert(payload).execute()

# ─────────────────────────────────────────────────────────────────────────
# 🧐 Cog principal
# ─────────────────────────────────────────────────────────────────────────
class TestQuestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}

    @commands.group(name="testquestion", aliases=["tq"], invoke_without_command=True)
    @no_dm()
    @commands.cooldown(rate=1, per=8, type=commands.BucketType.user)
    async def testquestion(self, ctx):
        guild_id = ctx.guild.id
        if self.active_sessions.get(guild_id):
            await ctx.reply("⚠️ Un quiz est déjà en cours.", mention_author=False)
            return

        self.active_sessions[guild_id] = True
        try:
            cards = await fetch_cards()
            main_card = next((c for c in cards if "desc" in c and is_clean_card(c)), None)
            if not main_card:
                await ctx.send("❌ Aucune carte valide trouvée.")
                self.active_sessions[guild_id] = None
                return

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
                    if c.get("name") != main_name and "desc" in c and get_type_group(c.get("type", "")) == type_group and is_clean_card(c)
                ]
                group.sort(key=lambda c: common_word_score(main_name, c["name"]) + similarity_ratio(main_name, c["name"]), reverse=True)

            if len(group) < 3:
                await ctx.send("❌ Pas assez de fausses cartes valides.")
                self.active_sessions[guild_id] = None
                return

            wrongs = random.sample(group, 3)
            all_choices = [main_name] + [c["name"] for c in wrongs]
            random.shuffle(all_choices)

            embed = discord.Embed(
                title="🧠 Quelle est cette carte ?",
                description=f"📘 **Type :** {main_type}\n📝 *{main_desc[:1500]}{'...' if len(main_desc) > 1500 else ''}*",
                color=discord.Color.purple()
            )
            embed.add_field(name="🔹 Archétype", value=f"||{archetype or 'Aucun'}||", inline=False)

            if main_type.lower().startswith("monstre"):
                embed.add_field(name="💥 ATK", value=str(main_card.get("atk", "—")), inline=True)
                embed.add_field(name="🛡️ DEF", value=str(main_card.get("def", "—")), inline=True)
                embed.add_field(name="⚙️ Niveau", value=str(main_card.get("level", "—")), inline=True)

            options_text = "\n".join(f"{REACTIONS[i]} - **{name}**" for i, name in enumerate(all_choices))
            embed.add_field(name="Choix", value=options_text, inline=False)

            quiz_msg = await ctx.send(embed=embed)
            self.active_sessions[guild_id] = quiz_msg
            for emoji in REACTIONS[:len(all_choices)]:
                try:
                    await quiz_msg.add_reaction(emoji)
                    await asyncio.sleep(0.4)
                except discord.HTTPException:
                    pass

            answers = {}
            winners = set()

            def check(reaction, user):
                return (
                    reaction.message.id == quiz_msg.id and
                    reaction.emoji in REACTIONS[:len(all_choices)] and
                    not user.bot and
                    user.id not in answers
                )

            try:
                while True:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    idx = REACTIONS.index(reaction.emoji)
                    chosen = all_choices[idx]
                    answers[user.id] = chosen
                    if chosen == main_name:
                        winners.add(user)
                    await update_streak(str(user.id), chosen == main_name)
            except asyncio.TimeoutError:
                pass

            correct_emoji = REACTIONS[all_choices.index(main_name)]
            result = discord.Embed(
                title="⏰ Temps écoulé !",
                description=f"✅ Réponse : {correct_emoji} **{main_name}**\n\n" +
                            (f"🎉 Gagnants : {', '.join(w.mention for w in winners)}" if winners else "😢 Personne n'a trouvé..."),
                color=discord.Color.green() if winners else discord.Color.red()
            )
            await ctx.send(embed=result)
            self.active_sessions[guild_id] = None
        except Exception as e:
            self.active_sessions[guild_id] = None
            await ctx.send(f"❌ Erreur : `{e}`")

    @testquestion.command(name="score", aliases=["streak", "s"])
    async def testquestion_score(self, ctx):
        user_id = str(ctx.author.id)
        try:
            response = supabase.table("ygo_streaks").select("current_streak", "best_streak").eq("user_id", user_id).execute()
            if response.data:
                streak = response.data[0]
                current = streak.get("current_streak", 0)
                best = streak.get("best_streak", 0)
                await ctx.send(
                    f"🔥 **{ctx.author.display_name}**, ta série actuelle est de **{current}** 🔁\n"
                    f"🏆 Ton record absolu est de **{best}** bonnes réponses consécutives !"
                )
            else:
                await ctx.send(
                    "📉 Tu n'as pas encore commencé de série.\n"
                    "Lance une question avec `!testquestion` pour démarrer ton streak !"
                )
        except Exception as e:
            print("[ERREUR STREAK]", e)
            await ctx.send("🚨 Une erreur est survenue en récupérant ta série.")

    @testquestion.command(name="top", aliases=["t"])
    async def testquestion_top(self, ctx):
        try:
            response = (
                supabase.table("ygo_streaks")
                .select("user_id, best_streak")
                .order("best_streak", desc=True)
                .limit(10)
                .execute()
            )
            if not response.data:
                await ctx.send("📉 Aucun streak enregistré pour le moment.")
                return

            leaderboard = []
            for index, row in enumerate(response.data, start=1):
                user_id = row["user_id"]
                best_streak = row.get("best_streak", 0)
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    username = user.name if user else f"Utilisateur inconnu ({user_id})"
                except:
                    username = f"Utilisateur inconnu ({user_id})"
                place = {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, f"`#{index}`")
                leaderboard.append(f"{place} **{username}** : 🔥 {best_streak}")

            embed = discord.Embed(
                title="🏆 Top 10 – Meilleures Séries",
                description="\n".join(leaderboard),
                color=discord.Color.gold()
            )
            embed.set_footer(text="Classement basé sur la meilleure série atteinte.")
            await ctx.send(embed=embed)
        except Exception as e:
            print("[ERREUR TOPQS]", e)
            await ctx.send("🚨 Une erreur est survenue lors du classement.")

# ─────────────────────────────────────────────────────────────────────────
# 🔌 Setup du cog
# ─────────────────────────────────────────────────────────────────────────
async def setup(bot):
    cog = TestQuestion(bot)
    for command in cog.get_commands():
        command.category = "🃏 Yu-Gi-Oh!"
    await bot.add_cog(cog)
