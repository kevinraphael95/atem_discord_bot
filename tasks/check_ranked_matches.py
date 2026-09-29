# ────────────────────────────────────────────────────────────────────────────────
# 📌 check_ranked_matches.py
# Objectif : Surveillance automatique des logs SQLite du serveur EDOPro VAACT
# Catégorie : Tâche automatisée
# Accès : Système
# Cooldown : 24.0h (1 exécution par jour pour préserver le serveur)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands, tasks
import sqlite3
import os

from utils.discord_utils import safe_send
from utils.elo_db import (
    init_elo_db, get_or_create_player, update_scores, 
    is_match_processed, calculate_elo
)

SERVER_DB_PATH = os.getenv("SERVER_DB_PATH", "./expansions/VAACT/cards.cdb")
RANKED_CHANNEL_ID = int(os.getenv("RANKED_CHANNEL_ID", "0"))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal de la tâche
# ────────────────────────────────────────────────────────────────────────────────
class RankedMatchTask(commands.Cog):
    """
    Tâche automatique vérifiant la base de données du serveur EDOPro
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_elo_db()
        self.check_vaact_matches.start()

    def cog_unload(self):
        self.check_vaact_matches.cancel()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Boucle de fond (Exécution 1x par jour pour réduire la charge serveur)
    # ────────────────────────────────────────────────────────────────────────────
    @tasks.loop(hours=24)
    async def check_vaact_matches(self):
        if not RANKED_CHANNEL_ID:
            return
            
        channel = self.bot.get_channel(RANKED_CHANNEL_ID)
        if not channel:
            return

        if not os.path.exists(SERVER_DB_PATH):
            return

        try:
            conn_srv = sqlite3.connect(SERVER_DB_PATH)
            cursor_srv = conn_srv.cursor()
            cursor_srv.execute("SELECT id, player1, player2, winner FROM matches")
            matches = cursor_srv.fetchall()
            conn_srv.close()

            for m_id, p1, p2, winner in matches:
                if is_match_processed(m_id):
                    continue

                r1_old, _, _ = get_or_create_player(p1)
                r2_old, _, _ = get_or_create_player(p2)
                p1_won = (winner == p1)
                
                r1_new, r2_new = calculate_elo(r1_old, r2_old, p1_won)
                update_scores(p1, p2, r1_new, r2_new, p1_won, m_id)

                embed = discord.Embed(
                    title="⚔️ VAACT Ranked — Duel Terminé !",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name=f"🏆 {p1} ({'Victoire' if p1_won else 'Défaite'})", 
                    value=f"ELO : `{r1_old}` ➔ **{r1_new}** ({'+' if r1_new >= r1_old else ''}{r1_new - r1_old})", 
                    inline=False
                )
                embed.add_field(
                    name=f"💀 {p2} ({'Victoire' if not p1_won else 'Défaite'})", 
                    value=f"ELO : `{r2_old}` ➔ **{r2_new}** ({'+' if r2_new >= r2_old else ''}{r2_new - r2_old})", 
                    inline=False
                )
                embed.set_footer(text="Atem ELO System • Server 146.59.225.202")

                await safe_send(channel, embed=embed)

        except Exception as e:
            print(f"[ERREUR RANKED TASK] {e}")

    @check_vaact_matches.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(RankedMatchTask(bot))
