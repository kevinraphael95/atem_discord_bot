# ================================================================================
# 📌 admin_editprofile.py
# Objectif : Interface visuelle pour modifier tous les champs d'un profil Discord
# Catégorie : Admin
# Accès : Administrateurs
# Cooldown : 1 utilisation / 5 sec
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
import sqlite3

from utils.vaact_utils import get_or_create_profile, DB_PATH
from utils.discord_utils import safe_send, safe_edit

# ================================================================================
# 🔒 Whitelist des champs autorisés (sécurité SQL)
# ================================================================================
ALLOWED_FIELDS = {
    "exp", "niveau", "cartefav", "fav_decks_vaact",
    "current_streak", "best_streak", "illu_streak",
    "best_illustreak", "vaact_name",
}

# ================================================================================
# 🎛️ Modal pour modifier un champ
# ================================================================================
class ProfileFieldModal(Modal):
    def __init__(self, field_name: str, current_value: str, callback):
        super().__init__(title=f"Modifier {field_name}")
        self.field_name  = field_name
        self.callback_fn = callback
        self.add_item(TextInput(
            label=f"Nouvelle valeur pour {field_name}",
            value=str(current_value) or "",
            required=False,
        ))

    async def on_submit(self, interaction: discord.Interaction):
        new_value = self.children[0].value
        await self.callback_fn(interaction, self.field_name, new_value)

# ================================================================================
# 🎛️ Menu déroulant de sélection du champ à modifier
# ================================================================================
class ProfileFieldSelect(Select):
    def __init__(self, parent_view: "ProfileEditView"):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="⭐ Niveau",             value="niveau",         emoji="⭐", description="Niveau global du joueur"),
            discord.SelectOption(label="💰 EXP",                value="exp",            emoji="💰", description="Expérience totale"),
            discord.SelectOption(label="🔥 Streak actuel",      value="current_streak", emoji="🔥", description="Série de victoires YGO en cours"),
            discord.SelectOption(label="🏅 Meilleur streak",    value="best_streak",    emoji="🏅", description="Record de victoires YGO"),
            discord.SelectOption(label="🎨 Illu streak",        value="illu_streak",    emoji="🎨", description="Série de victoires YGO Illustration"),
            discord.SelectOption(label="🌟 Best illu streak",   value="best_illustreak",emoji="🌟", description="Record de victoires YGO Illustration"),
            discord.SelectOption(label="🃏 Carte favorite",     value="cartefav",       emoji="🃏", description="Carte YGO préférée"),
            discord.SelectOption(label="🎴 Deck favori VAACT",  value="fav_decks_vaact",emoji="🎴", description="Deck favori VAACT"),
            discord.SelectOption(label="📝 Nom VAACT",          value="vaact_name",     emoji="📝", description="Nom affiché dans VAACT"),
        ]
        super().__init__(placeholder="🔧 Choisir un champ à modifier...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.parent_view

        # 🔒 Vérification admin
        if interaction.user.id != view.admin_user.id:
            return await interaction.response.send_message("❌ Ce panel n'est pas pour toi.", ephemeral=True)

        field_name = self.values[0]
        current    = view.profile.get(field_name, "")

        modal = ProfileFieldModal(field_name, current, view.modify_field)
        await interaction.response.send_modal(modal)

# ================================================================================
# 🎛️ View principale pour le profil
# ================================================================================
class ProfileEditView(View):
    def __init__(self, user_id: int, admin_user: discord.User):
        super().__init__(timeout=300)
        self.user_id         = user_id
        self.admin_user      = admin_user
        self.profile         = None
        self.embed_message   = None
        self.last_modified   = None

        # Ajout du menu déroulant
        self.add_item(ProfileFieldSelect(self))

    async def load_profile(self):
        self.profile = await get_or_create_profile(self.user_id)
        return self.profile

    def build_embed(self) -> discord.Embed:
        p = self.profile

        # == Titre avec indication de la dernière modification ==
        title = f"📄 Profil de {p['username']}"
        if self.last_modified:
            title += f"  *(modifié : {self.last_modified})*"

        embed = discord.Embed(title=title, color=discord.Color.blurple())

        # == Catégorie 1 : Progression ==
        embed.add_field(
            name="📊 Progression",
            value=(
                f"⭐ **Niveau** : `{p['niveau']}`\n"
                f"💰 **EXP** : `{p['exp']}`"
            ),
            inline=False
        )

        # == Catégorie 2 : Streaks de jeu ==
        embed.add_field(
            name="🎮 Streaks YGO",
            value=(
                f"🔥 **Actuel** : `{p['current_streak']}` *(record : {p['best_streak']})*\n"
                f"🎨 **Illu** : `{p['illu_streak']}` *(record : {p['best_illustreak']})*"
            ),
            inline=False
        )

        # == Catégorie 3 : Personnalisation ==
        embed.add_field(
            name="🎴 Personnalisation",
            value=(
                f"🃏 **Carte fav** : `{p['cartefav']}`\n"
                f"🎴 **Deck fav** : `{p['fav_decks_vaact']}`\n"
                f"📝 **Nom VAACT** : `{p['vaact_name']}`"
            ),
            inline=False
        )

        embed.set_footer(text="Utilise le menu ci-dessous pour modifier un champ.")
        return embed

    async def refresh_embed(self):
        if self.embed_message:
            try:
                await self.embed_message.edit(embed=self.build_embed(), view=self)
            except Exception:
                pass

    async def modify_field(self, interaction: discord.Interaction, field_name: str, new_value: str):
        # 🔒 Vérif admin
        if interaction.user.id != self.admin_user.id:
            return await interaction.response.send_message("❌ Ce panel n'est pas pour toi.", ephemeral=True)

        # 🔒 Whitelist
        if field_name not in ALLOWED_FIELDS:
            return await interaction.response.send_message("❌ Champ non autorisé.", ephemeral=True)

        try:
            # ✅ Conversion en int si possible (pour exp, niveau, streaks)
            if field_name in ("exp", "niveau", "current_streak", "best_streak", "illu_streak", "best_illustreak"):
                try:
                    new_value = int(new_value)
                except (ValueError, TypeError):
                    return await interaction.response.send_message("❌ Valeur numérique attendue.", ephemeral=True)

            conn   = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE profil SET {field_name} = ? WHERE user_id = ?",
                (new_value, str(self.user_id))
            )
            conn.commit()
            conn.close()

            # Recharge
            self.profile       = await get_or_create_profile(self.user_id)
            self.last_modified = field_name
            await self.refresh_embed()

            # Log admin (dans le terminal)
            print(f"[ADMIN] {interaction.user} a modifié {field_name} de {self.user_id} → {new_value}")

            await interaction.response.send_message(f"✅ `{field_name}` mis à jour !", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.embed_message:
            try:
                await self.embed_message.edit(view=self)
            except Exception:
                pass

# ================================================================================
# 🧠 Cog principal avec méthode commune pour slash & prefix
# ================================================================================
class AdminEditProfile(commands.Cog):
    """Commande /editprofile et !editprofile — Interface visuelle pour modifier un profil"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_menu(self, target: discord.User, admin: discord.User, channel: discord.abc.Messageable):
        view = ProfileEditView(target.id, admin)
        await view.load_profile()
        embed = view.build_embed()
        view.embed_message = await safe_send(channel, embed=embed, view=view)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="editprofile", help="Ouvre une interface visuelle pour modifier un profil")
    @commands.has_permissions(administrator=True)
    async def editprofile(self, ctx: commands.Context, member: discord.Member):
        await self._send_menu(member, ctx.author, ctx.channel)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="editprofile", description="Ouvre une interface visuelle pour modifier un profil")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_editprofile(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await self._send_menu(member, interaction.user, interaction.channel)
        await interaction.delete_original_response()

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = AdminEditProfile(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
