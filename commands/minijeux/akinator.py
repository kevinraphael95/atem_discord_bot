# ────────────────────────────────────────────────────────────────────────────────
# 📌 akinator.py — Commande interactive /akinator et !akinator
# Objectif : Deviner la carte Yu-Gi-Oh à laquelle pense le joueur via l'API YGOPRODeck
# Catégorie : Minijeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import aiohttp
import os
import random
from utils.discord_utils import safe_send, safe_edit, safe_respond

QUESTIONS_JSON_PATH = "data/akinator_questions.json"
CACHE_PATH = "data/cards_cache.json"

# ────────────────────────────────────────────────────────────────────────────────
def load_questions():
    try:
        with open(QUESTIONS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {QUESTIONS_JSON_PATH} : {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
class IntelligentQuestionView(View):
    def __init__(self, bot, questions, cards):
        super().__init__(timeout=None)
        self.bot = bot
        self.questions = questions
        self.remaining_cards = cards
        self.message = None
        self.current_question = None
        self.current_value = None
        self.scores = {c['id']: 0 for c in self.remaining_cards}

    def most_discriminant_question(self):
        best_q = None
        best_score = -1
        for q in self.questions:
            if not q["filter_value"]:
                continue
            for val in q["filter_value"]:
                count = sum(1 for c in self.remaining_cards if val in c.get(q["filter_key"], []))
                if count > best_score:
                    best_score = count
                    best_q = q
                    self.current_value = val
        return best_q

    def next_question(self):
        if not self.questions or len(self.remaining_cards) <= 3:
            return None
        self.current_question = self.most_discriminant_question()
        return self.current_question

    async def ask_question(self, interaction=None):
        q = self.next_question()
        # Proposer carte probable à tout moment
        best_cards = sorted(self.remaining_cards, key=lambda c: self.scores[c['id']], reverse=True)[:3]

        if not q:
            embed = discord.Embed(
                title="🔮 Résultat Akinator",
                description="\n".join(f"• {c['name']}" for c in best_cards),
                color=discord.Color.purple()
            )
            if interaction:
                await safe_edit(interaction.message, embed=embed, view=None)
            return embed

        # Affichage question + proposition probable
        self.clear_items()
        self.add_item(AnswerButton(self, "Oui"))
        self.add_item(AnswerButton(self, "Non"))
        self.add_item(AnswerButton(self, "Ne sais pas"))

        question_text = q["text"].replace("{value}", self.current_value or "...")
        embed = discord.Embed(
            title="❓ Question Akinator",
            description=f"{question_text}\n\n**Carte probable:** {best_cards[0]['name'] if best_cards else '...'}",
            color=discord.Color.blue()
        )
        if interaction:
            await safe_edit(interaction.message, embed=embed, view=self)
        else:
            return embed

    async def process_answer(self, answer: str, interaction: discord.Interaction):
        q = self.current_question
        val = self.current_value
        for c in self.remaining_cards:
            values = c.get(q["filter_key"], [])
            if answer == "Oui" and val in values:
                self.scores[c['id']] += 1
            elif answer == "Non" and val in values:
                self.scores[c['id']] -= 1
            # "Ne sais pas" ne change pas le score

        if q in self.questions:
            self.questions.remove(q)
        await self.ask_question(interaction)

class AnswerButton(Button):
    def __init__(self, parent_view: IntelligentQuestionView, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.parent_view.process_answer(self.label, interaction)
            await interaction.response.defer()
        except Exception as e:
            print(f"[ERREUR Button] {e}")

# ────────────────────────────────────────────────────────────────────────────────
class AkinatorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cards_cache = None

    async def fetch_cards(self):
        if self.cards_cache:
            return self.cards_cache
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    self.cards_cache = json.load(f)
                    return self.cards_cache
            except Exception as e:
                print(f"[ERREUR CACHE] {e}")

        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                cards = []
                for c in data["data"]:
                    type_subtype = c.get("type", "").split()
                    if c.get("race"):
                        type_subtype.append(c["race"])
                    attribute = [c["attribute"]] if c.get("attribute") else []
                    archetype = [c["archetype"]] if c.get("archetype") else []
                    stats = []
                    atk, defe, level, link = c.get("atk"), c.get("def"), c.get("level"), c.get("linkval")
                    if atk: stats += [f"ATK>={x}" for x in [1000,1500,2000,2500] if atk>=x]
                    if defe: stats += [f"DEF>={x}" for x in [1000,1500,2000,2500] if defe>=x]
                    if level: stats += [f"Level>={x}" for x in [4,5,6,7,8,10] if level>=x]
                    if link: stats.append(f"Link-{link}")
                    desc = (c.get("desc") or "").lower()
                    type_str = (c.get("type") or "").lower()
                    effect = []
                    keywords = {
                        "Fusion":["fusion"],"Ritual":["ritual"],"Special Summon":["special summon"],
                        "Continuous":["continuous"],"Equip":["equip"],"Field":["field"],"Quick-Play":["quick-play"],
                        "Token":["token"],"Pendulum":["pendulum"],"Link":["link"],"Synchro":["synchro"],
                        "Xyz":["xyz"],"Flip":["flip"],"Union":["union"],"Spirit":["spirit"],
                        "Draw":["draw a card"],"Destroy":["destroy"],"Negate":["negate"],
                        "ATK modification":["gain atk","increase atk","lose atk","reduce atk"],
                        "DEF modification":["gain def","increase def","lose def","reduce def"],
                        "Search":["add 1","add one","search your deck"],
                        "Recycle":["return","shuffle into the deck"],
                        "Mill":["send the top","send cards from the top"],
                        "Tribute":["tribute"],"Burn":["inflict","damage your opponent"],
                        "Life Point Gain":["gain life points","increase your lp"],"Piercing":["piercing","inflict battle damage"],
                        "Direct Attack":["direct attack"]
                    }
                    for key,pats in keywords.items():
                        if any(p in desc for p in pats) or any(p in type_str for p in pats):
                            effect.append(key)
                    cards.append({
                        "id": c.get("id"),
                        "name": c.get("name","Inconnue"),
                        "type_subtype": type_subtype,
                        "attribute": attribute,
                        "archetype": archetype,
                        "stats": stats,
                        "effect": effect
                    })

        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cards, f, ensure_ascii=False, indent=4)
        self.cards_cache = cards
        return cards

    async def _send_akinator(self, channel: discord.abc.Messageable):
        questions = load_questions()
        if not questions:
            await safe_send(channel, "❌ Impossible de charger les questions Akinator.")
            return
        cards = await self.fetch_cards()
        if not cards:
            await safe_send(channel, "❌ Impossible de récupérer les cartes depuis l'API YGOPRODeck.")
            return
        view = IntelligentQuestionView(self.bot, questions, cards)
        embed = await view.ask_question()
        view.message = await safe_send(channel, embed=embed, view=view)

    @app_commands.command(name="akinator", description="Le bot devine la carte Yu-Gi-Oh à laquelle tu penses !")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_akinator(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            await self._send_akinator(interaction.channel)
            await interaction.delete_original_response()
        except Exception as e:
            print(f"[ERREUR /akinator] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    @commands.command(name="akinator")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_akinator(self, ctx: commands.Context):
        try:
            await self._send_akinator(ctx.channel)
        except Exception as e:
            print(f"[ERREUR !akinator] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AkinatorCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Minijeux"
    await bot.add_cog(cog)
