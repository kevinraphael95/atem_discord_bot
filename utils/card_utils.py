# ────────────────────────────────────────────────────────────────────────────────
# 📦 utils/card_utils.py
# Objectif : Centraliser la recherche de cartes Yu-Gi-Oh! (API YGOPRODeck)
# Version : ✅ Optimisée, session réutilisable, gestion d’erreurs
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import aiohttp
import urllib.parse
import random
from typing import Tuple, List, Optional, Dict

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Client HTTP global réutilisable
# ────────────────────────────────────────────────────────────────────────────────
_session: Optional[aiohttp.ClientSession] = None

def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fonctions de recherche
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_card_multilang(nom: str) -> Tuple[Optional[Dict], str]:
    """Recherche exacte du nom dans plusieurs langues (fr, de, it, pt, en)."""
    nom_encode = urllib.parse.quote(nom)
    languages = ["fr", "de", "it", "pt", ""]
    session = get_session()

    for lang in languages:
        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
        if lang:
            url += f"&language={lang}"
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and data["data"]:
                        return data["data"][0], (lang or "en")
        except Exception as e:
            print(f"[Erreur fetch_card_multilang] {e}")
    return None, "?"

async def fetch_card_fuzzy(nom: str) -> List[Dict]:
    """Recherche floue (fname=...) pour trouver des cartes similaires."""
    nom_encode = urllib.parse.quote(nom)
    session = get_session()
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}&language=fr"
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", [])
    except Exception as e:
        print(f"[Erreur fetch_card_fuzzy] {e}")
    return []

async def fetch_random_card() -> Tuple[Optional[Dict], str]:
    """Récupère une carte aléatoire en français si possible."""
    session = get_session()
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr"
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status != 200:
                return None, "?"
            data = await resp.json()
            cards = data.get("data", [])
            if not cards:
                return None, "?"
            card = random.choice(cards)
            return card, "fr"
    except Exception as e:
        print(f"[Erreur fetch_random_card] {e}")
        return None, "?"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Fonction principale
# ────────────────────────────────────────────────────────────────────────────────
async def search_card(nom: str) -> Tuple[Optional[Dict], str, str]:
    """
    Recherche une carte :
      - Exact match multi-langue
      - Fuzzy match si rien trouvé
      - Retourne (carte, langue, message)
    """
    carte, langue = await fetch_card_multilang(nom)
    if carte:
        return carte, langue, ""

    fuzzy = await fetch_card_fuzzy(nom)
    if fuzzy:
        return fuzzy[0], "fr", ""

    return None, "?", f"❌ Désolé, aucune carte trouvée pour `{nom}`."

# ────────────────────────────────────────────────────────────────────────────────
# 📊 META — Cartes les plus jouées
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_meta_cards(limit: int = 10) -> List[Dict]:
    """
    Récupère une sélection de cartes 'META' actuelles.
    (Tri simulé par ATK décroissante + usage_rate)
    """
    session = get_session()
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr&sort=atk&misc=yes"
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            cards = data.get("data", [])
            if not cards:
                return []

            # Trier par ATK décroissante
            cards = sorted(cards, key=lambda c: c.get("atk", 0) or 0, reverse=True)

            # Ajouter usage_rate simulé
            for i, c in enumerate(cards[:limit]):
                c["usage_rate"] = round(100 - (i * (100 / limit)), 1)

            return cards[:limit]
    except Exception as e:
        print(f"[Erreur fetch_meta_cards] {e}")
        return []
