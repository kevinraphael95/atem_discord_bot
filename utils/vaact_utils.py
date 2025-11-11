# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact_utils.py — Utilitaires pour profils et gestion de l’EXP/Niveau
# Objectif : Récupérer ou créer un profil, gérer les streaks et l’EXP des utilisateurs
# Catégorie : Utilitaires
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Gestion des profils
# ────────────────────────────────────────────────────────────────────────────────
async def get_or_create_profile(user_id: int | str, username: str = None) -> dict:
    """
    Récupère le profil d'un utilisateur ou le crée s'il n'existe pas.
    Renvoie le dictionnaire du profil.
    """
    user_id_str = str(user_id)
    try:
        resp = supabase.table("profil").select("*").eq("user_id", user_id_str).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]

        # Crée un profil par défaut si inexistant
        profile = {
            "user_id": user_id_str,
            "username": username or f"ID {user_id_str}",
            "niveau": 0,
            "exp": 0,
            "cartefav": "Non défini",
            "vaact_name": "Non défini",
            "fav_decks_vaact": "Non défini",
            "current_streak": 0,
            "best_streak": 0,
            "illu_streak": 0,
            "best_illustreak": 0
        }
        supabase.table("profil").upsert(profile).execute()
        return profile

    except Exception as e:
        print(f"[Supabase] Impossible de récupérer ou créer le profil : {e}")
        # Retourne un profil par défaut “erreur” si problème
        return {
            "user_id": user_id_str,
            "username": username or f"ID {user_id_str}",
            "niveau": 0,
            "exp": 0,
            "cartefav": "Erreur",
            "vaact_name": "Erreur",
            "fav_decks_vaact": "Erreur",
            "current_streak": 0,
            "best_streak": 0,
            "illu_streak": 0,
            "best_illustreak": 0
        }

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Gestion de l’EXP et des niveaux
# ────────────────────────────────────────────────────────────────────────────────
async def add_exp_for_streak(user_id: int | str, new_best_streak: int) -> dict:
    """
    Met à jour l'EXP et le niveau d'un profil selon la série max.
    5 points de streak max = 1 niveau.
    """
    user_id_str = str(user_id)
    try:
        # Récupérer le profil
        resp = supabase.table("profil").select("*").eq("user_id", user_id_str).execute()
        profile = resp.data[0] if resp.data else await get_or_create_profile(user_id_str)

        # Calcul du niveau et de l'EXP
        exp_from_streak = new_best_streak // 5  # 5 streak max = 1 niveau
        if exp_from_streak > profile.get("niveau", 0):
            profile["niveau"] = exp_from_streak
            profile["exp"] = new_best_streak

        # Sauvegarde
        supabase.table("profil").upsert(profile).execute()
        return profile

    except Exception as e:
        print(f"[Supabase] Impossible de mettre à jour l'EXP pour {user_id_str} : {e}")
        return profile if 'profile' in locals() else {}
