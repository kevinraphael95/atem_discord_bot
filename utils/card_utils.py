# ────────────────────────────────────────────────────────────────────────────────
# 📦 utils/card_utils.py
# Objectif : Centraliser la recherche de cartes Yu-Gi-Oh! (API YGOPRODeck)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
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
    """Récupère une carte aléatoire en français si possible."""
    async with aiohttp.ClientSession() as session:
        # 1️⃣ Récupérer toutes les cartes FR
        async with session.get("https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr") as resp:
            if resp.status != 200:
                return None, "?"
            data = await resp.json()
            cards = data.get("data", [])
            if not cards:
                return None, "?"

        # 2️⃣ Tirer une carte aléatoire
        import random
        card = random.choice(cards)
        return card, "fr"



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

# ────────────────────────────────────────────────────────────────────────────────
# 📊 META — Cartes les plus jouées
# ────────────────────────────────────────────────────────────────────────────────
async def fetch_meta_cards(limit: int = 10) -> list[dict]:
    """
    Récupère une sélection de cartes 'META' actuelles.
    (L’API YGOPRODeck ne fournit pas de taux d’utilisation officiel, donc on simule
     un classement basé sur les ATK les plus élevées pour le visuel.)
    """
    async with aiohttp.ClientSession() as session:
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?language=fr&sort=atk&misc=yes"
        async with session.get(url) as resp:
            if resp.status != 200:
                return []

            data = await resp.json()
            cards = data.get("data", [])
            if not cards:
                return []

            # Trier par ATK décroissante
            cards = sorted(cards, key=lambda c: c.get("atk", 0) or 0, reverse=True)

            # Simuler un taux d’utilisation décroissant
            for i, c in enumerate(cards[:limit]):
                c["usage_rate"] = round(100 - (i * (100 / limit)), 1)

            return cards[:limit]
