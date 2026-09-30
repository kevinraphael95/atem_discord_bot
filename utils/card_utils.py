# ================================================================================
# 📦 utils/card_utils.py
# Objectif : Centraliser la recherche de cartes Yu-Gi-Oh! (API YGOPRODeck)
# Version optimisée : récupération à la demande (0 cache, 0 RAM)
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import aiohttp
import urllib.parse
import random
import asyncio

# ================================================================================
# 🎲 Récupération à la demande
# ================================================================================

async def fetch_random_card(session: aiohttp.ClientSession) -> tuple[dict | None, str]:
    """Récupère UNE carte aléatoire (1 seul appel API)."""
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?random=yes&language=fr"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None, "?"
            data = await resp.json()
            cards = data.get("data", [])
            if not cards:
                return None, "?"
            return cards[0], "fr"
    except Exception as e:
        print(f"[card_utils] fetch_random_card : {e}")
        return None, "?"


async def fetch_random_cards(session: aiohttp.ClientSession, n: int = 5) -> list[dict]:
    """Récupère N cartes aléatoires (N appels API en parallèle)."""
    tasks = [fetch_random_card(session) for _ in range(n)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [c for c, _ in results if isinstance(c, dict)]


async def fetch_cards_by_type(session: aiohttp.ClientSession, card_type: str, n: int = 5) -> list[dict]:
    """Récupère N cartes d'un type donné (1 appel API + sample local)."""
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?type={urllib.parse.quote(card_type)}&language=fr"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            all_cards = data.get("data", [])
            return random.sample(all_cards, k=min(n, len(all_cards)))
    except Exception as e:
        print(f"[card_utils] fetch_cards_by_type : {e}")
        return []


async def fetch_cards_by_archetype(session: aiohttp.ClientSession, archetype: str, n: int = 5) -> list[dict]:
    """Récupère N cartes d'un archétype donné."""
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?archetype={urllib.parse.quote(archetype)}&language=fr"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            all_cards = data.get("data", [])
            return random.sample(all_cards, k=min(n, len(all_cards)))
    except Exception as e:
        print(f"[card_utils] fetch_cards_by_archetype : {e}")
        return []


async def fetch_staple_cards(session: aiohttp.ClientSession) -> list[dict]:
    """Récupère les cartes 'staple' (1 appel API)."""
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes&language=fr"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("data", [])
    except Exception as e:
        print(f"[card_utils] fetch_staple_cards : {e}")
        return []


# ================================================================================
# 🔍 Récupération complète (1 seul appel)
# ================================================================================

async def fetch_card_full(nom: str, session: aiohttp.ClientSession) -> dict | None:
    """
    Récupère une carte complète en 1 seul appel API.
    Essaie d'abord en FR, puis fallback EN si non trouvé.
    """
    nom_encode = urllib.parse.quote(nom)
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}&language=fr"

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                # Fallback sans langue (anglais)
                url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
                async with session.get(url) as resp2:
                    if resp2.status != 200:
                        return None
                    data = await resp2.json()
                    cards = data.get("data", [])
                    return cards[0] if cards else None
            data = await resp.json()
            cards = data.get("data", [])
            return cards[0] if cards else None
    except Exception as e:
        print(f"[card_utils] fetch_card_full : {e}")
        return None


# ================================================================================
# 🔧 Fonctions de recherche (inchangées)
# ================================================================================

async def fetch_card_multilang(nom: str, session: aiohttp.ClientSession) -> tuple[dict | None, str]:
    """Recherche exacte du nom dans plusieurs langues (fr, de, it, pt, en)."""
    nom_encode = urllib.parse.quote(nom)
    for lang in ["fr", "de", "it", "pt", ""]:
        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}"
        if lang:
            url += f"&language={lang}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        return data["data"][0], (lang or "en")
        except Exception:
            continue
    return None, "?"


async def fetch_card_fuzzy(nom: str, session: aiohttp.ClientSession) -> list[dict]:
    """Recherche floue (fname=...) pour trouver des cartes similaires."""
    nom_encode = urllib.parse.quote(nom)
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}&language=fr"
    async with session.get(url) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("data", [])
    return []


async def search_card(nom: str, session: aiohttp.ClientSession) -> tuple[dict | None, str, str]:
    """Recherche une carte : exact multi-langue, puis fuzzy."""
    carte, langue = await fetch_card_multilang(nom, session)
    if carte:
        return carte, langue, ""
    fuzzy = await fetch_card_fuzzy(nom, session)
    if fuzzy:
        return fuzzy[0], "fr", ""
    return None, "?", f"❌ Désolé, aucune carte trouvée pour `{nom}`."
