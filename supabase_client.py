import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Charge .env si présent (utile localement)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("❌ SUPABASE_URL ou SUPABASE_KEY est manquant dans les variables d'environnement.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Client Supabase initialisé avec succès.")
