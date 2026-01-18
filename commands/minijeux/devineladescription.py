# ────────────────────────────────────────────────────────────────────────────────
# 📌 devineladescription.py — Commande interactive !devineladescription
# Objectif : Deviner une carte Yu-Gi-Oh à partir de sa description
# Catégorie : Minijeux
# Accès : Public
# Cooldown : 1 utilisation / 8 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
import random
import re
from difflib import SequenceMatcher

from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_reply, safe_edit  
from utils.vaact_utils import add_exp_for_streak

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
# 🔗 Requêtes API YGO
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_cards(session, limit=100):
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
    async with session.get(url) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()
        return random.sample(data.get("data", []), min(limit, len(data.get("data", []))))

async def fetch_archetype_cards(session, archetype):
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={archetype}&language=fr"
    async with session.get(url) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()
        return data.get("data", [])

# ────────────────────────────────────────────────────────────────────────────────
# 🔄 Mise à jour des streaks et EXP
# ────────────────────────────────────────────────────────────────────────────────
async def update_streak(user_id: str, correct: bool, bot=None):
    username = f"ID {user_id}"
    if bot:
        try:
            user = await bot.fetch_user(int(user_id))
            username = user.name if user else username
        except:
            pass

    row = supabase.table("profil").select("*").eq("user_id", user_id).execute().data
    current = row[0]["current_streak"] if row else 0
    best    = row[0].get("best_streak",0) if row else 0
    new_streak = current + 1 if correct else 0
    new_best   = max(best, new_streak)

    payload = {
        "user_id": user_id,
        "username": username,
        "cartefav": row[0].get("cartefav","Non défini") if row else "Non défini",
        "vaact_name": row[0].get("vaact_name","Non défini") if row else "Non défini",
        "fav_decks_vaact": row[0].get("fav_decks_vaact","Non défini") if row else "Non défini",
        "current_streak": new_streak,
        "best_streak": new_best
    }
    supabase.table("profil").upsert(payload).execute()
    if new_best > best:
        await add_exp_for_streak(user_id, new_best)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class DevineLaDescription(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}  # guild_id → quiz en cours

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 View & Buttons
    # ────────────────────────────────────────────────────────────────────────────
    class QuizView(View):
        def __init__(self, bot, choices, main_name):
            super().__init__(timeout=60)
            self.bot = bot
            self.choices = choices
            self.main_name = main_name
            self.answers = {}
            for idx, name in enumerate(choices):
                self.add_item(DevineLaDescription.QuizButton(label=name, idx=idx, parent_view=self))

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            if hasattr(self,"message"):
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
                    self.parent_view.choices[self.idx] == self.parent_view.main_name,
                    bot=self.parent_view.bot
                )
            await interaction.response.send_message(
                f"✅ Réponse enregistrée : **{self.label}**",
                ephemeral=True
            )

    # ────────────────────────────────────────────────────────────────────────────
    # 💬 Commande principale
    # ────────────────────────────────────────────────────────────────────────────
    @commands.group(
        name="devineladescription",
        aliases=["dld","description","d","devinedescription","dd"],
        invoke_without_command=True
    )
    @no_dm()
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def devineladescription(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        if self.active_sessions.get(guild_id):
            return await safe_reply(ctx,"⚠️ Un quiz est déjà en cours.",mention_author=False)
        self.active_sessions[guild_id] = True

        try:
            session = self.bot.aiohttp_session

            cards = await fetch_cards(session)
            main_card = next((c for c in cards if "desc" in c and is_clean_card(c)), None)
            if not main_card:
                return await safe_send(ctx,"❌ Aucune carte valide trouvée.")

            main_name = main_card["name"]
            main_desc = censor_card_name(main_card["desc"], main_name)
            main_type = main_card.get("type","")
            archetype = main_card.get("archetype")
            type_group = get_type_group(main_type)

            if archetype:
                group = await fetch_archetype_cards(session, archetype)
                group = [c for c in group if c.get("name") != main_name and "desc" in c]
            else:
                group = [
                    c for c in cards
                    if c.get("name") != main_name
                    and "desc" in c
                    and get_type_group(c.get("type","")) == type_group
                    and is_clean_card(c)
                ]
                group.sort(
                    key=lambda c: common_word_score(main_name,c["name"])
                    + similarity_ratio(main_name,c["name"]),
                    reverse=True
                )

            if len(group) < 3:
                return await safe_send(ctx,"❌ Pas assez de fausses cartes valides.")

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

            view = self.QuizView(self.bot,choices,main_name)
            view.message = await safe_send(ctx,embed=embed,view=view)
            await view.wait()

            winners = [
                self.bot.get_user(uid)
                for uid,idx in view.answers.items()
                if choices[idx]==main_name
            ]

            result_embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=(
                    f"✅ Réponse : **{main_name}**\n"
                    + (
                        f"🎉 Gagnants : {', '.join(w.mention for w in winners if w)}"
                        if winners else "😢 Personne n'a trouvé..."
                    )
                ),
                color=discord.Color.green() if winners else discord.Color.red()
            )
            await safe_send(ctx,embed=result_embed)

        except Exception as e:
            await safe_send(ctx,f"❌ Erreur : `{e}`")
        finally:
            self.active_sessions[guild_id] = None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Score et top
    # ────────────────────────────────────────────────────────────────────────────
    @devineladescription.command(name="score",aliases=["streak","s"])
    async def devineladescription_score(self,ctx:commands.Context):
        user_id = str(ctx.author.id)
        try:
            resp = supabase.table("profil").select("current_streak,best_streak").eq("user_id",user_id).execute()
            if resp.data:
                cur = resp.data[0].get("current_streak",0)
                best = resp.data[0].get("best_streak",0)
                embed = discord.Embed(
                    title=f"🔥 Série de {ctx.author.display_name}",
                    color=discord.Color.blurple()
                )
                embed.add_field(name="Série actuelle", value=f"**{cur}**", inline=False)
                embed.add_field(name="Record absolu", value=f"**{best}**", inline=False)
                await safe_send(ctx,embed=embed)
            else:
                await safe_send(
                    ctx,
                    embed=discord.Embed(
                        title="📉 Pas encore de série",
                        description="Lance `!devineladescription` pour démarrer ta série !",
                        color=discord.Color.red()
                    )
                )
        except Exception:
            await safe_send(ctx,"🚨 Erreur lors de la récupération de ta série.")

    @devineladescription.command(name="top",aliases=["t"])
    async def devineladescription_top(self,ctx:commands.Context):
        try:
            resp = supabase.table("profil") \
                .select("user_id,best_streak") \
                .gt("best_streak",0) \
                .order("best_streak",desc=True) \
                .limit(10) \
                .execute()

            data = resp.data
            if not data:
                return await safe_send(ctx,"📉 Aucun streak enregistré.")

            lines=[]
            for i,row in enumerate(data,start=1):
                uid=row.get("user_id")
                best=row.get("best_streak",0)
                user = await self.bot.fetch_user(int(uid)) if uid else None
                name = user.name if user else f"ID {uid}"
                medal = {1:"🥇",2:"🥈",3:"🥉"}.get(i,f"`#{i}`")
                lines.append(f"{medal} **{name}** – 🔥 {best}")

            embed=discord.Embed(
                title="🏆 Top 10 Séries",
                description="\n".join(lines),
                color=discord.Color.gold()
            )
            await safe_send(ctx,embed=embed)
        except Exception:
            await safe_send(ctx,"🚨 Erreur lors du classement.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot:commands.Bot):
    cog = DevineLaDescription(bot)
    for command in cog.get_commands():
        command.category = "Minijeux"
    await bot.add_cog(cog)
