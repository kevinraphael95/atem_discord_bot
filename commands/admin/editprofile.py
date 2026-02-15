# ────────────────────────────────────────────────────────────────────────────────
# 📌 admin_editprofile.py
# Objectif : Interface visuelle pour modifier tous les champs d’un profil Discord
# Catégorie : Admin
# Accès : Administrateurs
# Cooldown : 1 utilisation / 5 sec
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import sqlite3

from utils.vaact_utils import get_or_create_profile, DB_PATH
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Modal pour modifier un champ
# ────────────────────────────────────────────────────────────────────────────────
class ProfileFieldModal(Modal):
    def __init__(self, field_name: str, current_value: str, callback):
        super().__init__(title=f"Modifier {field_name}")
        self.field_name = field_name
        self.callback_fn = callback
        self.add_item(TextInput(label=f"Nouvelle valeur pour {field_name}", value=str(current_value) or ""))

    async def on_submit(self, interaction: discord.Interaction):
        new_value = self.children[0].value
        await self.callback_fn(interaction, self.field_name, new_value)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ View principale pour le profil
# ────────────────────────────────────────────────────────────────────────────────
class ProfileEditView(View):
    def __init__(self, user_id: int, admin_user: discord.User):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.admin_user = admin_user
        self.profile = None
        self.embed_message = None

    async def load_profile(self):
        self.profile = await get_or_create_profile(self.user_id)
        return self.profile

    def build_embed(self):
        p = self.profile
        embed = discord.Embed(title=f"📄 Profil de {p['username']}", color=discord.Color.blue())
        embed.add_field(name="💰 EXP", value=p['exp'], inline=True)
        embed.add_field(name="⭐ Niveau", value=p['niveau'], inline=True)
        embed.add_field(name="🏆 Carte favorite", value=p['cartefav'], inline=True)
        embed.add_field(name="🎴 Deck favori", value=p['fav_decks_vaact'], inline=True)
        embed.add_field(name="🔥 Streak actuel", value=p['current_streak'], inline=True)
        embed.add_field(name="🏅 Meilleur streak", value=p['best_streak'], inline=True)
        embed.add_field(name="🎨 Illu streak", value=p['illu_streak'], inline=True)
        embed.add_field(name="🌟 Meilleur illu streak", value=p['best_illustreak'], inline=True)
        embed.add_field(name="📝 Nom VAACT", value=p['vaact_name'], inline=True)
        return embed

    async def refresh_embed(self):
        if self.embed_message:
            await self.embed_message.edit(embed=self.build_embed(), view=self)

    async def modify_field(self, interaction: discord.Interaction, field_name: str, new_value):
        if interaction.user.id != self.admin_user.id:
            return await interaction.response.send_message("❌ Ce panel n’est pas pour toi.", ephemeral=True)
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(f"UPDATE profil SET {field_name} = ? WHERE user_id = ?", (new_value, str(self.user_id)))
            conn.commit()
            conn.close()
            self.profile = await get_or_create_profile(self.user_id)
            await self.refresh_embed()
            await interaction.response.send_message(f"✅ `{field_name}` mis à jour !", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.embed_message:
            await self.embed_message.edit(view=self)

    # ─────────── Buttons ───────────
    @discord.ui.button(label="💰 EXP", style=discord.ButtonStyle.primary)
    async def exp_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("exp", self.profile['exp'], self.modify_field)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⭐ Niveau", style=discord.ButtonStyle.primary)
    async def niveau_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("niveau", self.profile['niveau'], self.modify_field)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🏆 Carte favorite", style=discord.ButtonStyle.secondary)
    async def cartefav_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("cartefav", self.profile['cartefav'], self.modify_field)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎴 Deck favori", style=discord.ButtonStyle.secondary)
    async def deckfav_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("fav_decks_vaact", self.profile['fav_decks_vaact'], self.modify_field)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔥 Streak actuel", style=discord.ButtonStyle.success)
    async def streak_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("current_streak", self.profile['current_streak'], self.modify_field)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🏅 Meilleur streak", style=discord.ButtonStyle.success)
    async def best_streak_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("best_streak", self.profile['best_streak'], self.modify_field)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎨 Illu streak", style=discord.ButtonStyle.success)
    async def illu_streak_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("illu_streak", self.profile['illu_streak'], self.modify_field)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🌟 Meilleur illu streak", style=discord.ButtonStyle.success)
    async def best_illu_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("best_illustreak", self.profile['best_illustreak'], self.modify_field)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📝 Nom VAACT", style=discord.ButtonStyle.secondary)
    async def vaact_name_button(self, interaction: discord.Interaction, button: Button):
        modal = ProfileFieldModal("vaact_name", self.profile['vaact_name'], self.modify_field)
        await interaction.response.send_modal(modal)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec méthode commune pour slash & prefix
# ────────────────────────────────────────────────────────────────────────────────
class AdminEditProfile(commands.Cog):
    """
    Commande /editprofile et !editprofile — Interface visuelle pour modifier un profil
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_menu(self, user: discord.User, channel: discord.abc.Messageable):
        view = ProfileEditView(user.id, user)
        await view.load_profile()
        embed = view.build_embed()
        view.embed_message = await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="editprofile", help="Ouvre une interface visuelle pour modifier un profil")
    @commands.has_permissions(administrator=True)
    async def editprofile(self, ctx: commands.Context, member: discord.Member):
        await self._send_menu(member, ctx.channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="editprofile", description="Ouvre une interface visuelle pour modifier un profil")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_editprofile(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await self._send_menu(member, interaction.channel)
        await interaction.delete_original_response()

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AdminEditProfile(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
