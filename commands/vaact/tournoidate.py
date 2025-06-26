# ────────────────────────────────────────────────────────────────────────────────
# 📌 TournoiDate.py — Commande interactive !TournoiDate
# Objectif : Modifier la date du tournoi enregistrée sur Supabase via menus déroulants
# Catégorie : VAACT
# Accès : Modérateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Select
from datetime import datetime
import os
from supabase import create_client, Client  # pip install supabase

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Configuration Supabase
# ────────────────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue interactive pour sélectionner la date
# ────────────────────────────────────────────────────────────────────────────────
class DateStepView(View):
    def __init__(self, bot, ctx, selected=None, step="year"):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.selected = selected or {}
        self.step = step

        now = datetime.now()

        if step == "year":
            years = [str(y) for y in range(now.year, now.year + 3)]
            self.add_item(self.YearSelect(years))
        elif step == "month":
            months = [str(m) for m in range(1, 13)]
            self.add_item(self.MonthSelect(months))
        elif step == "day_range":
            self.add_item(self.DayRangeSelect())
        elif step == "day":
            if self.selected.get("day_range") == "1-15":
                days = list(range(1, 16))
            else:
                days = list(range(16, 32))
            self.add_item(self.DaySelect(days))
        elif step == "hour":
            hours = [str(h) for h in range(0, 24)]
            self.add_item(self.HourSelect(hours))

    def YearSelect(self, years):
        class _Select(Select):
            def __init__(s):
                super().__init__(placeholder="Choisis une année",
                                 options=[discord.SelectOption(label=y, value=y) for y in years])

            async def callback(s, interaction):
                self.selected["year"] = int(s.values[0])
                await interaction.response.edit_message(
                    content=f"Année sélectionnée : {s.values[0]}",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="month")
                )

        return _Select()

    def MonthSelect(self, months):
        class _Select(Select):
            def __init__(s):
                super().__init__(placeholder="Choisis un mois",
                                 options=[discord.SelectOption(label=m, value=m) for m in months])

            async def callback(s, interaction):
                self.selected["month"] = int(s.values[0])
                await interaction.response.edit_message(
                    content=f"{self.selected['year']} - Mois sélectionné : {s.values[0]}",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="day_range")
                )
        return _Select()

    def DayRangeSelect(self):
        class _Select(Select):
            def __init__(s):
                super().__init__(placeholder="Plage de jours",
                                 options=[
                                     discord.SelectOption(label="Jours 1-15", value="1-15"),
                                     discord.SelectOption(label="Jours 16-31", value="16-31"),
                                 ])

            async def callback(s, interaction):
                self.selected["day_range"] = s.values[0]
                await interaction.response.edit_message(
                    content=f"{self.selected['year']}-{self.selected['month']} — Plage : {s.values[0]}",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="day")
                )
        return _Select()

    def DaySelect(self, days):
        class _Select(Select):
            def __init__(s):
                super().__init__(placeholder="Jour",
                                 options=[discord.SelectOption(label=str(d), value=str(d)) for d in days])

            async def callback(s, interaction):
                self.selected["day"] = int(s.values[0])
                await interaction.response.edit_message(
                    content=f"{self.selected['year']}-{self.selected['month']}-{self.selected['day']}",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="hour")
                )
        return _Select()

    def HourSelect(self, hours):
        class _Select(Select):
            def __init__(s):
                super().__init__(placeholder="Heure (24h)",
                                 options=[discord.SelectOption(label=h, value=h) for h in hours])

            async def callback(s, interaction):
                self.selected["hour"] = int(s.values[0])
                try:
                    dt = datetime(
                        self.selected["year"],
                        self.selected["month"],
                        self.selected["day"],
                        self.selected["hour"]
                    )
                    response = supabase.table("tournoi_info").update({"prochaine_date": dt.isoformat()}).eq("id", 1).execute()

                    if response.status_code in (200, 204):
                        await interaction.response.edit_message(
                            content=f"✅ Date mise à jour : {dt.strftime('%d/%m/%Y %Hh')}",
                            view=None
                        )
                    else:
                        await interaction.response.edit_message(
                            content=f"❌ Erreur Supabase : code {response.status_code}",
                            view=None
                        )



                except Exception as e:
                    await interaction.response.edit_message(
                        content=f"❌ Erreur : {e}",
                        view=None
                    )
        return _Select()


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiDate(commands.Cog):
    """
    Commande !TournoiDate — Permet à un modérateur de définir la date du tournoi via menus déroulants
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tournoidate", aliases=["settournoi"], description="Changer la date du prochain tournoi VAACT.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def TournoiDate(self, ctx):
        try:
            view = DateStepView(self.bot, ctx)
            await ctx.send("🗓️ Choisis la date du tournoi VAACT :", view=view)
        except Exception as e:
            print(f"[ERREUR TournoiDate] {e}")
            await ctx.send(f"❌ Une erreur est survenue : `{e}`")


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiDate(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "VAACT"
    await bot.add_cog(cog)
