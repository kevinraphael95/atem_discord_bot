# ────────────────────────────────────────────────────────────────────────────────
# 📌 tournoi_date.py — Commande interactive !tournoidate
# Objectif : Modifier la date et le lieu du tournoi enregistrés sur Supabase via menus déroulants
# Catégorie : 🧠 VAACT
# Accès : Modérateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
from datetime import datetime

import discord
from discord.ext import commands
from discord.ui import View, Select, Button
from supabase import create_client, Client  # pip install supabase

from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Configuration Supabase
# ────────────────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Sélecteurs en étapes pour construire la date + lieu
# ────────────────────────────────────────────────────────────────────────────────
class DateStepView(View):
    """
    Vue interactive pour sélectionner année → mois → plage de jours → jour → heure → lieu.
    """
    def __init__(self, bot, ctx, selected=None, step="year"):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.selected = selected or {}
        self.step = step
        self.author_id = ctx.author.id

        # Ajouter bouton pour supprimer la date + lieu
        self.add_item(DeleteDateButton(ctx))

        now = datetime.now()
        if step == "year":
            years = [str(y) for y in range(now.year, now.year + 3)]
            self.add_item(self._make_year_select(years))
        elif step == "month":
            months = [str(m) for m in range(1, 13)]
            self.add_item(self._make_month_select(months))
        elif step == "day_range":
            self.add_item(self._make_day_range_select())
        elif step == "day":
            if self.selected.get("day_range") == "1-15":
                days = list(range(1, 16))
            else:
                days = list(range(16, 32))
            self.add_item(self._make_day_select(days))
        elif step == "hour":
            hours = [str(h) for h in range(0, 24)]
            self.add_item(self._make_hour_select(hours))
        elif step == "location":
            locations = ["Ludotrotter", "Ailleurs"]
            self.add_item(self._make_location_select(locations))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Tu ne peux pas interagir avec ce menu.",
                ephemeral=True
            )
            return False
        return True

    # ────────────────────────────────────────────────────────────────────────
    # 📅 Sélecteurs
    # ────────────────────────────────────────────────────────────────────────
    def _make_year_select(self, years):
        class YearSelect(Select):
            def __init__(inner):
                super().__init__(
                    placeholder="Choisis une année",
                    options=[discord.SelectOption(label=y, value=y) for y in years]
                )

            async def callback(inner, interaction: discord.Interaction):
                self.selected["year"] = int(inner.values[0])
                await interaction.response.edit_message(
                    content=f"🗓️ Année sélectionnée : **{inner.values[0]}**",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="month")
                )

        return YearSelect()

    def _make_month_select(self, months):
        class MonthSelect(Select):
            def __init__(inner):
                super().__init__(
                    placeholder="Choisis un mois",
                    options=[discord.SelectOption(label=m, value=m) for m in months]
                )

            async def callback(inner, interaction: discord.Interaction):
                self.selected["month"] = int(inner.values[0])
                await interaction.response.edit_message(
                    content=f"🗓️ {self.selected['year']} – Mois sélectionné : **{inner.values[0]}**",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="day_range")
                )

        return MonthSelect()

    def _make_day_range_select(self):
        class DayRangeSelect(Select):
            def __init__(inner):
                super().__init__(
                    placeholder="Plage de jours",
                    options=[
                        discord.SelectOption(label="Jours 1-15", value="1-15"),
                        discord.SelectOption(label="Jours 16-31", value="16-31"),
                    ]
                )

            async def callback(inner, interaction: discord.Interaction):
                self.selected["day_range"] = inner.values[0]
                await interaction.response.edit_message(
                    content=f"🗓️ {self.selected['year']}-{self.selected['month']} — Plage : **{inner.values[0]}**",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="day")
                )

        return DayRangeSelect()

    def _make_day_select(self, days):
        class DaySelect(Select):
            def __init__(inner):
                super().__init__(
                    placeholder="Choisis un jour",
                    options=[discord.SelectOption(label=str(d), value=str(d)) for d in days]
                )

            async def callback(inner, interaction: discord.Interaction):
                self.selected["day"] = int(inner.values[0])
                await interaction.response.edit_message(
                    content=f"🗓️ {self.selected['year']}-{self.selected['month']}-{self.selected['day']}",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="hour")
                )

        return DaySelect()

    def _make_hour_select(self, hours):
        class HourSelect(Select):
            def __init__(inner):
                super().__init__(
                    placeholder="Choisis une heure (24h)",
                    options=[discord.SelectOption(label=h, value=h) for h in hours]
                )

            async def callback(inner, interaction: discord.Interaction):
                self.selected["hour"] = int(inner.values[0])
                await interaction.response.edit_message(
                    content=f"🗓️ Heure sélectionnée : **{inner.values[0]}h**",
                    view=DateStepView(self.bot, self.ctx, self.selected, step="location")
                )

        return HourSelect()

    def _make_location_select(self, locations):
        class LocationSelect(Select):
            def __init__(inner):
                super().__init__(
                    placeholder="Choisis le lieu",
                    options=[discord.SelectOption(label=l, value=l) for l in locations]
                )

            async def callback(inner, interaction: discord.Interaction):
                self.selected["location"] = inner.values[0]

                dt = datetime(
                    self.selected["year"],
                    self.selected["month"],
                    self.selected["day"],
                    self.selected["hour"]
                )

                supabase.table("tournoi_info").upsert({
                    "id": 1,
                    "prochaine_date": dt.isoformat(),
                    "lieu": self.selected["location"]
                }).execute()

                await interaction.response.edit_message(
                    content=f"✅ Date et lieu mis à jour : **{dt.strftime('%d/%m/%Y %Hh')}** à **{self.selected['location']}**",
                    view=None
                )

        return LocationSelect()


# ────────────────────────────────────────────────────────────────────────────────
# 🎮 UI — Bouton pour supprimer la date + lieu
# ────────────────────────────────────────────────────────────────
class DeleteDateButton(Button):
    def __init__(self, ctx):
        super().__init__(label="Supprimer la date", style=discord.ButtonStyle.danger, emoji="🗑️")
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                "❌ Action non autorisée.",
                ephemeral=True
            )

        supabase.table("tournoi_info").update(
            {"prochaine_date": None, "lieu": None}
        ).eq("id", 1).execute()

        await interaction.response.edit_message(
            content="🗑️ La date et le lieu du tournoi ont été supprimés.",
            view=None
        )


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TournoiDate(commands.Cog):
    """
    Commande !tournoidate — Permet à un modérateur de définir la date et le lieu du tournoi.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="tournoidate",
        aliases=["settournoi"],
        help="(Admin) 🛠️ Change la date et le lieu du prochain tournoi VAACT.",
        description="Permet de sélectionner année/mois/jour/heure/lieu via menus déroulants."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def tournoidate(self, ctx: commands.Context):
        try:
            view = DateStepView(self.bot, ctx)
            await safe_send(ctx, "🗓️ Choisis la date et le lieu du tournoi ou supprime-les :", view=view)
        except Exception as e:
            await safe_send(ctx, f"❌ Une erreur est survenue : `{e}`")


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TournoiDate(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
