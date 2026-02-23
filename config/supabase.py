import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_SECRET") or os.getenv("SUPABASE_ANON_PUBLIC")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL or SUPABASE_KEY not found in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
