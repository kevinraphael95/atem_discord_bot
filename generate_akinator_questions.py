# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ generate_akinator_questions.py
# Objectif : Générer automatiquement akinator_questions.json
# Source : API YGOPRODeck
# ────────────────────────────────────────────────────────────────────────────────

import json
import aiohttp
import asyncio
import os

OUTPUT_PATH = "data/akinator_questions.json"

# ────────────────────────────────────────────────────────────────────────────────
# 📡 Récupération des données YGOPRODeck
# ────────────────────────────────────────────────────────────────────────────────
async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

async def generate_questions():
    print("📡 Récupération des données depuis l'API YGOPRODeck...")

    # Archétypes
    archetypes_data = await fetch("https://db.ygoprodeck.com/api/v7/archetypes.php")
    archetypes = sorted([a["archetype_name"] for a in archetypes_data])

    # Cartes pour extraire types/attributs/effets
    cards_data = await fetch("https://db.ygoprodeck.com/api/v7/cardinfo.php")
    cards = cards_data["data"]

    # Attributs
    attributes = sorted({c["attribute"] for c in cards if "attribute" in c})

    # Types & sous-types
    types = sorted({c["type"] for c in cards if "type" in c})

    # Effets (analyse basique des textes)
    effects_keywords = [
        "Fusion","Ritual","Synchro","Xyz","Pendulum","Link","Special Summon",
        "Flip","Union","Spirit","Gemini","Continuous","Equip","Field","Quick-Play","Counter",
        "Token","Search","Draw","Destroy","Negate","Recycle","Mill","Banish","Tribute",
        "Burn","Life Point Gain","Piercing","Direct Attack","ATK modification","DEF modification",
        "Protection","Immunity","Bounce","Hand Trap","Floodgate"
    ]

    # Stats (paliers définis manuellement)
    stats = [
        "ATK>=500","ATK>=1000","ATK>=1500","ATK>=2000","ATK>=2500","ATK>=3000","ATK>=4000",
        "DEF>=500","DEF>=1000","DEF>=1500","DEF>=2000","DEF>=2500","DEF>=3000",
        "Level>=1","Level>=2","Level>=3","Level>=4","Level>=5","Level>=6","Level>=7","Level>=8","Level>=10","Level>=12",
        "Link>=1","Link>=2","Link>=3","Link>=4","Link>=5","Link>=6"
    ]

    # ────────────────────────────────────────────────────────────────────────────
    # Construction du JSON
    # ────────────────────────────────────────────────────────────────────────────
    questions = [
        {
            "text": "Est-ce que le type ou sous-type de la carte est {value} ?",
            "filter_key": "type_subtype",
            "filter_value": types
        },
        {
            "text": "Est-ce que l'attribut du monstre est {value} ?",
            "filter_key": "attribute",
            "filter_value": attributes
        },
        {
            "text": "Est-ce que la carte appartient à l'archétype {value} ?",
            "filter_key": "archetype",
            "filter_value": archetypes
        },
        {
            "text": "La carte a-t-elle un effet ou une mécanique {value} ?",
            "filter_key": "effect",
            "filter_value": effects_keywords
        },
        {
            "text": "La carte a-t-elle des statistiques ou un niveau correspondant à {value} ?",
            "filter_key": "stats",
            "filter_value": stats
        }
    ]

    # ────────────────────────────────────────────────────────────────────────────
    # Sauvegarde
    # ────────────────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=4, ensure_ascii=False)

    print(f"✅ Fichier généré : {OUTPUT_PATH} ({len(archetypes)} archétypes inclus)")

# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(generate_questions())
