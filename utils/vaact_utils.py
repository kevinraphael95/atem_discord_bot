# ────────────────────────────────────────────────────────────────────────────────
# 📌 vaact_utils.py — Utilitaires pour profils et gestion de l’EXP/Niveau
# Objectif : Récupérer ou créer un profil, gérer les streaks et l’EXP des utilisateurs
# Catégorie : Utilitaires
# Accès : Tous
# Base locale SQLite
# ────────────────────────────────────────────────────────────────────────────────

import sqlite3
from pathlib import Path

DB_PATH = Path("data/profil.db")

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Gestion des profils
# ────────────────────────────────────────────────────────────────────────────────
async def get_or_create_profile(user_id: int | str, username: str = None) -> dict:
    user_id_str = str(user_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Création de la table si elle n'existe pas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profil (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            niveau INTEGER DEFAULT 0,
            exp INTEGER DEFAULT 0,
            cartefav TEXT DEFAULT 'Non défini',
            vaact_name TEXT DEFAULT 'Non défini',
            fav_decks_vaact TEXT DEFAULT 'Non défini',
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            illu_streak INTEGER DEFAULT 0,
            best_illustreak INTEGER DEFAULT 0
        )
    """)

    # Vérifie si le profil existe
    cursor.execute("SELECT * FROM profil WHERE user_id = ?", (user_id_str,))
    row = cursor.fetchone()

    if row:
        profile = {
            "user_id": row[0],
            "username": row[1],
            "niveau": row[2],
            "exp": row[3],
            "cartefav": row[4],
            "vaact_name": row[5],
            "fav_decks_vaact": row[6],
            "current_streak": row[7],
            "best_streak": row[8],
            "illu_streak": row[9],
            "best_illustreak": row[10]
        }
    else:
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
        cursor.execute("""
            INSERT INTO profil (
                user_id, username, niveau, exp, cartefav, vaact_name,
                fav_decks_vaact, current_streak, best_streak, illu_streak, best_illustreak
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile["user_id"], profile["username"], profile["niveau"], profile["exp"],
            profile["cartefav"], profile["vaact_name"], profile["fav_decks_vaact"],
            profile["current_streak"], profile["best_streak"], profile["illu_streak"],
            profile["best_illustreak"]
        ))
        conn.commit()

    conn.close()
    return profile

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Gestion de l’EXP et des niveaux
# ────────────────────────────────────────────────────────────────────────────────
async def add_exp(user_id: int | str, exp_gain: int) -> dict:
    """
    Ajoute de l'EXP à un profil. 5 EXP = 1 niveau.
    """
    profile = await get_or_create_profile(user_id)
    profile["exp"] = (profile.get("exp") or 0) + exp_gain
    profile["niveau"] = profile["exp"] // 5

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE profil SET exp = ?, niveau = ? WHERE user_id = ?
    """, (profile["exp"], profile["niveau"], str(user_id)))
    conn.commit()
    conn.close()
    return profile

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
