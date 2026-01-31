import random
import aiohttp

BASE_URL = "https://api.tcgdex.net/v2/en"

async def fetch_card_by_name(name: str, session: aiohttp.ClientSession):
    async with session.get(f"{BASE_URL}/cards", params={"name": name}) as r:
        if r.status != 200:
            return None
        data = await r.json()
        return random.choice(data) if data else None

async def fetch_card_by_id(card_id: str, session: aiohttp.ClientSession):
    async with session.get(f"{BASE_URL}/cards/{card_id}") as r:
        if r.status != 200:
            return None
        return await r.json()

async def fetch_random_card(session: aiohttp.ClientSession):
    async with session.get(f"{BASE_URL}/cards") as r:
        if r.status != 200:
            return None
        data = await r.json()
        return random.choice(data) if data else None
