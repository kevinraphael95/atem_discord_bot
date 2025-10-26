# ────────────────────────────────────────────────────────────────────────────────
# 📦 utils/card_utils.py
# Objectif : Centraliser la recherche de cartes Yu-Gi-Oh! (API YGOPRODeck)
# ────────────────────────────────────────────────────────────────────────────────

import aiohttp
import urllib.parse

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Fonctions de recherche
# ────────────────────────────────────────────────────────────────────────────────

async def fetch_card_multilang(nom: str) -> tuple[dict | None, str]:
    """Recherche exacte du nom dans plusieurs langues (fr, de, it, pt, en)."""
    nom_encode = urllib.parse.quote(nom)
    languages = ["fr", "de", "it", "pt", ""]
    async with aiohttp.ClientSession() as session:
        for lang in languages:
            url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
            if lang:
                url += f"&language={lang}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        return data["data"][0], (lang or "en")
    return None, "?"


async def fetch_card_fuzzy(nom: str) -> list[dict]:
    """Recherche floue (fname=...) pour trouver des cartes similaires."""
    nom_encode = urllib.parse.quote(nom)
    async with aiohttp.ClientSession() as session:
        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}&language=fr"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", [])
    return []


async def fetch_random_card() -> tuple[dict | None, str]:
    """Récupère une carte aléatoire (FR prioritaire, fallback EN)."""
    async with aiohttp.ClientSession() as session:
        for lang in ["fr", "en"]:
            async with session.get(f"https://db.ygoprodeck.com/api/v7/randomcard.php?language={lang}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data:
                        data = data["data"][0]
                    return data, lang
    return None, "?"


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Fonction principale
# ────────────────────────────────────────────────────────────────────────────────

async def search_card(nom: str) -> tuple[dict | None, str, str]:
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
