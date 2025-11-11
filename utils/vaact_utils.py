# utils/vaact_utils.py
from utils.supabase_client import supabase

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
