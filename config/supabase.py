"""
Supabase client management.

- **Auth operations** use a lightweight sync client (anon key).  The
  sign_in_with_oauth call is purely local (~2 ms, no network) and
  exchange_code_for_session needs the PKCE verifier stored in-process,
  so the sync client is the safest choice here.

- **Database operations** use a persistent AsyncClient (service-role key)
  initialized once during the app lifespan.  The long-lived httpx
  connection pool avoids the ~1 s cold-connect penalty per query.
"""
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, acreate_client, Client, AsyncClient

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_SECRET", "")
ANON_KEY: str = os.getenv("SUPABASE_ANON_PUBLIC", "")

if not SUPABASE_URL or not SERVICE_ROLE_KEY or not ANON_KEY:
    raise ValueError("SUPABASE_URL or SUPABASE_KEY not found in environment variables")

# ── Sync client for Auth (anon key) ─────────────────────────
# Lightweight, safe for PKCE — verifier stays in-process memory.
supabase: Client = create_client(SUPABASE_URL, ANON_KEY)


# ── Persistent async client for DB operations (service-role) ─
@dataclass
class _AsyncAdmin:
    """
    Holder for the long-lived async admin client.
    Populated once by ``init()`` during the FastAPI lifespan.
    """
    client: Optional[AsyncClient] = field(default=None)

    async def init(self) -> None:
        self.client = await acreate_client(SUPABASE_URL, SERVICE_ROLE_KEY)

    async def aclose(self) -> None:
        if self.client is not None:
            try:
                # Supabase AsyncClient may not expose aclose; swallow errors.
                await self.client.aclose()  # type: ignore[attr-defined]
            except Exception:
                pass

    # Convenience: supabase_admin.table("x") delegates to the real client.
    def table(self, name: str):
        if self.client is None:
            raise RuntimeError(
                "Async Supabase admin client not initialised. "
                "Ensure the FastAPI lifespan has run."
            )
        return self.client.table(name)


supabase_admin = _AsyncAdmin()
