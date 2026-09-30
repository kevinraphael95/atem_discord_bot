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

async def _fetch_by_id(session: aiohttp.ClientSession, card_id: int,
                       language: str | None = None,
                       with_genesys: bool = False) -> dict | None:
    """Récupère une carte par id, avec options langue + genesys."""
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?id={card_id}&misc=yes"
    if language:
        url += f"&language={language}"
    if with_genesys:
        url += "&format=genesys"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            cards = data.get("data", [])
            return cards[0] if cards else None
    except Exception as e:
        print(f"[card_utils] _fetch_by_id({language}, genesys={with_genesys}) : {e}")
        return None


async def fetch_genesys_ocg(session: aiohttp.ClientSession, card_id: int) -> int | None:
    """Récupère uniquement les points Genesys OCG."""
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?id={card_id}&format=genesys%20ocg&misc=yes"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            cards = data.get("data", [])
            if not cards:
                return None
            return cards[0].get("genesys_ocg_points")
    except Exception as e:
        print(f"[card_utils] fetch_genesys_ocg : {e}")
        return None


async def fetch_random_card(session: aiohttp.ClientSession) -> tuple[dict | None, str]:
    """Récupère UNE carte aléatoire, en FR si possible + nom EN conservé."""
    url = "https://db.ygoprodeck.com/api/v7/randomcard.php"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None, "?"
            data = await resp.json()
            card = data.get("data", [{}])[0] if isinstance(data.get("data"), list) else data
            if not card or "id" not in card:
                return None, "?"
    except Exception as e:
        print(f"[card_utils] fetch_random_card : {e}")
        return None, "?"

    # Récupère FR + EN en parallèle
    card_fr, card_en = await asyncio.gather(
        _fetch_by_id(session, card["id"], language="fr"),
        _fetch_by_id(session, card["id"], language=None),
    )

    base = card_fr or card_en or card
    if card_en:
        base["name_en"] = card_en.get("name")
        base["desc_en"] = card_en.get("desc")
    else:
        base.setdefault("name_en", base.get("name"))

    return base, ("fr" if card_fr else "en")


async def fetch_random_cards(session: aiohttp.ClientSession, n: int = 5) -> list[dict]:
    tasks = [fetch_random_card(session) for _ in range(n)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [c for c, _ in results if isinstance(c, dict)]


async def fetch_cards_by_type(session: aiohttp.ClientSession, card_type: str, n: int = 5) -> list[dict]:
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
# 🔍 Récupération complète
# ================================================================================

async def fetch_card_full(nom: str | None, session: aiohttp.ClientSession) -> dict | None:
    """
    Récupère une carte complète.

    - Si nom=None ou "random" → carte aléatoire (FR si possible)
    - Sinon → recherche par nom (FR puis fallback EN)
    - Conserve le nom anglais dans 'name_en'
    - Si la carte a des points Genesys TCG > 0, récupère aussi l'OCG
    """
    if not nom or str(nom).lower() == "random":
        card, _ = await fetch_random_card(session)
        if card and card.get("id"):
            await _enrich_genesys(session, card)
        return card

    nom_encode = urllib.parse.quote(str(nom))
    card = None

    # 1) FR
    try:
        url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}&language=fr&misc=yes"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                cards = data.get("data", [])
                card = cards[0] if cards else None
    except Exception as e:
        print(f"[card_utils] fetch_card_full (FR) : {e}")

    # 2) Fallback EN
    if not card:
        try:
            url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nom_encode}&misc=yes"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                cards = data.get("data", [])
                card = cards[0] if cards else None
        except Exception as e:
            print(f"[card_utils] fetch_card_full (EN) : {e}")
            return None

    if not card:
        return None

    # 3) Nom EN conservé
    card_en = await _fetch_by_id(session, card["id"], language=None)
    if card_en:
        card["name_en"] = card_en.get("name")
        card["desc_en"] = card_en.get("desc")
    else:
        card["name_en"] = card.get("name")

    # 4) Points Genesys
    await _enrich_genesys(session, card)

    return card


async def _enrich_genesys(session: aiohttp.ClientSession, card: dict):
    """
    Ajoute genesys_points (TCG) et genesys_ocg_points si dispo.
    Appel TCG fait seulement si pas déjà présent.
    Appel OCG seulement si TCG > 0 (économie d'API).
    """
    if "genesys_points" not in card:
        card_gs = await _fetch_by_id(session, card["id"], with_genesys=True)
        if card_gs:
            card["genesys_points"] = card_gs.get("genesys_points")

    tcg = card.get("genesys_points")
    if tcg and tcg > 0 and "genesys_ocg_points" not in card:
        ocg = await fetch_genesys_ocg(session, card["id"])
        if ocg is not None:
            card["genesys_ocg_points"] = ocg


# ================================================================================
# 🔧 Fonctions de recherche (obsolètes — utiliser fetch_card_full)
# ================================================================================

async def fetch_card_multilang(nom: str, session: aiohttp.ClientSession) -> tuple[dict | None, str]:
    nom_encode = urllib.parse.quote(str(nom))
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
    nom_encode = urllib.parse.quote(str(nom))
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={nom_encode}&language=fr"
    async with session.get(url) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("data", [])
    return []


async def search_card(nom: str, session: aiohttp.ClientSession) -> tuple[dict | None, str, str]:
    carte, langue = await fetch_card_multilang(nom, session)
    if carte:
        return carte, langue, ""
    fuzzy = await fetch_card_fuzzy(nom, session)
    if fuzzy:
        return fuzzy[0], "fr", ""
    return None, "?", f"❌ Désolé, aucune carte trouvée pour `{nom}`."
