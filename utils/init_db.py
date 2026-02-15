# ────────────────────────────────────────────────────────────────────────────────
# 📌 init_db.py
# Objectif : Initialiser les bases SQLite locales pour le bot (tournoi + profils)
# Catégorie : 🧠 Utils
# Accès : Tous
# Cooldown : /
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
import sqlite3
from datetime import datetime

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Configuration SQLite
# ────────────────────────────────────────────────────────────────────────────────
DB_DIR = "database"
TOURNOI_DB_PATH = os.path.join(DB_DIR, "tournoi.db")
PROFIL_DB_PATH = os.path.join(DB_DIR, "profil.db")
os.makedirs(DB_DIR, exist_ok=True)

def get_conn(db_type="tournoi"):
    """Retourne une connexion SQLite vers la base locale choisie."""
    if db_type == "tournoi":
        return sqlite3.connect(TOURNOI_DB_PATH)
    elif db_type == "profil":
        return sqlite3.connect(PROFIL_DB_PATH)
    else:
        raise ValueError("Type de DB inconnu. Choisir 'tournoi' ou 'profil'.")

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Initialisation des tables
# ────────────────────────────────────────────────────────────────────────────────
def init_db():
    """Crée les tables tournoi_info et profil si elles n'existent pas."""

    # ─── Base tournoi.db ─────────────────────────────
    conn = get_conn("tournoi")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tournoi_info (
        id INTEGER PRIMARY KEY,
        prochaine_date TEXT NOT NULL,
        lieu TEXT
    )
    """)
    # Initialiser une ligne si vide
    cursor.execute("SELECT COUNT(*) FROM tournoi_info")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO tournoi_info (id, prochaine_date, lieu) VALUES (1, ?, ?)",
            (datetime(2000, 1, 1).isoformat(), None)
        )
    conn.commit()
    conn.close()

    # ─── Base profil.db ──────────────────────────────
    conn = get_conn("profil")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profil (
        user_id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        cartefav TEXT DEFAULT 'Non défini',
        vaact_name TEXT DEFAULT 'Non défini',
        fav_decks_vaact TEXT DEFAULT 'Non défini',
        current_streak INTEGER DEFAULT 0 NOT NULL,
        best_streak INTEGER DEFAULT 0,
        illu_streak INTEGER DEFAULT 0,
        best_illustreak INTEGER DEFAULT 0,
        niveau INTEGER DEFAULT 0,
        exp INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_profil_user_id
    ON profil(user_id)
    """)
    conn.commit()
    conn.close()

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Si lancé directement
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print(f"✅ Bases initialisées : {TOURNOI_DB_PATH} + {PROFIL_DB_PATH}")
