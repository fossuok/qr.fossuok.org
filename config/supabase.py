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
    raise ValueError("Missing required Supabase environment variables")

supabase: Client = create_client(SUPABASE_URL, ANON_KEY)


@dataclass
class _AsyncAdmin:
    client: Optional[AsyncClient] = field(default=None)

    async def init(self) -> None:
        self.client = await acreate_client(SUPABASE_URL, SERVICE_ROLE_KEY)

    async def aclose(self) -> None:
        if self.client is not None:
            try:
                await self.client.aclose()
            except Exception:
                pass

    def table(self, name: str):
        if self.client is None:
            raise RuntimeError(
                "Async Supabase admin client not initialised. "
                "Ensure the FastAPI lifespan has run."
            )
        return self.client.table(name)


supabase_admin = _AsyncAdmin()