# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact_utils.py — Utilitaires pour profils et gestion de l’EXP/Niveau
# Objectif : Récupérer ou créer un profil, gérer les streaks et l’EXP des utilisateurs
# Catégorie : Utilitaires
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Gestion des profils
# ────────────────────────────────────────────────────────────────────────────────
async def get_or_create_profile(user_id: int | str, username: str = None) -> dict:
    user_id_str = str(user_id)
    try:
        resp = supabase.table("profil").select("*").eq("user_id", user_id_str).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]

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
async def add_exp(user_id: int | str, exp_gain: int) -> dict:
    """
    Ajoute de l'EXP à un profil. 5 EXP = 1 niveau.
    """
    user_id_str = str(user_id)
    try:
        resp = supabase.table("profil").select("*").eq("user_id", user_id_str).execute()
        profile = resp.data[0] if resp.data else await get_or_create_profile(user_id_str)

        profile["exp"] = (profile.get("exp") or 0) + exp_gain
        profile["niveau"] = (profile["exp"] or 0) // 5

        supabase.table("profil").upsert(profile).execute()
        return profile

    except Exception as e:
        print(f"[Supabase] Impossible d'ajouter de l'EXP pour {user_id_str} : {e}")
        return profile if 'profile' in locals() else {}

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 EXP pour les streaks (record)
# ────────────────────────────────────────────────────────────────────────────────
async def add_exp_for_streak(user_id: int | str, new_best_streak: int) -> dict:
    """
    Ajoute de l'EXP uniquement si l'utilisateur bat son record de streak.
    La récompense est proportionnelle à la nouvelle meilleure série.
    """
    # Chaque point de streak = 1 EXP par exemple
    exp_gain = new_best_streak
    return await add_exp(user_id, exp_gain)
