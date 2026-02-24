import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_SECRET")
ANON_KEY: str | None = os.getenv("SUPABASE_ANON_PUBLIC")

if not SUPABASE_URL or not SERVICE_ROLE_KEY or not ANON_KEY:
    raise ValueError("SUPABASE_URL or SUPABASE_KEY not found in environment variables")


# Standard client for Auth operations (Anon Key)
# Use this when you need to exchange codes or handle user-specific auth sessions.
supabase: Client = create_client(SUPABASE_URL, ANON_KEY)

# Admin client with Service Role bypass (Service Role Key)
# Use this for all backend database operations to bypass RLS.
supabase_admin: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
