# ────────────────────────────────────────────────────────────────────────────────
# 📌 elo_db.py
# Objectif : Fonctions d'interaction et de calcul pour la base de données ELO
# Catégorie : Utilitaire
# Accès : Interne
# Cooldown : Aucun
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import sqlite3
import os

ATEM_ELO_DB = os.path.join("data", "atem_elo.db")

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Fonctions de gestion SQLite
# ────────────────────────────────────────────────────────────────────────────────
def init_elo_db():
    """Initialise la structure de la base de données ELO si elle n'existe pas."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(ATEM_ELO_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            username TEXT PRIMARY KEY,
            elo INTEGER DEFAULT 1000,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_matches (
            match_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def get_or_create_player(username: str):
    """Récupère ou crée le profil ELO d'un joueur."""
    conn = sqlite3.connect(ATEM_ELO_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT elo, wins, losses FROM players WHERE username = ?", (username,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO players (username, elo, wins, losses) VALUES (?, 1000, 0, 0)", (username,))
        conn.commit()
        conn.close()
        return 1000, 0, 0
    conn.close()
    return row[0], row[1], row[2]

def update_scores(p1: str, p2: str, r1_new: int, r2_new: int, p1_won: bool, match_id: int):
    """Met à jour les scores ELO et enregistre le match comme traité."""
    conn = sqlite3.connect(ATEM_ELO_DB)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET elo = ?, wins = wins + ?, losses = losses + ? WHERE username = ?",
        (r1_new, 1 if p1_won else 0, 0 if p1_won else 1, p1)
    )
    cursor.execute(
        "UPDATE players SET elo = ?, wins = wins + ?, losses = losses + ? WHERE username = ?",
        (r2_new, 0 if p1_won else 1, 1 if p1_won else 0, p2)
    )
    cursor.execute("INSERT INTO processed_matches (match_id) VALUES (?)", (match_id,))
    conn.commit()
    conn.close()

def is_match_processed(match_id: int) -> bool:
    """Vérifie si un match a déjà été calculé."""
    conn = sqlite3.connect(ATEM_ELO_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT match_id FROM processed_matches WHERE match_id = ?", (match_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def calculate_elo(r1: int, r2: int, p1_won: bool, k: int = 32):
    """Calcule les nouveaux scores ELO selon la formule standard."""
    e1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
    e2 = 1 / (1 + 10 ** ((r1 - r2) / 400))
    s1 = 1.0 if p1_won else 0.0
    s2 = 0.0 if p1_won else 1.0
    
    new_r1 = round(r1 + k * (s1 - e1))
    new_r2 = round(r2 + k * (s2 - e2))
    return new_r1, new_r2
