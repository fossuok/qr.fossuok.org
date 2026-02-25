import asyncio
import time
from typing import Optional

from config.supabase import supabase_admin
from models.event import Event

# --- In-memory TTL cache for the active event ---
_TTL_SECONDS = 300  # 5 minutes — active event rarely changes mid-session
_event_cache: Optional[tuple[Event, float]] = None
_cache_lock = asyncio.Lock()


def invalidate_event_cache() -> None:
    """Call this if an admin changes the active event so the cache refreshes immediately."""
    global _event_cache
    _event_cache = None


async def get_active_event() -> Optional[Event]:
    """
    Fetches the first active event from the database.
    Result is cached in memory for _TTL_SECONDS to avoid repeated Supabase round-trips.
    Uses the persistent async client — no new connection per call.
    """
    global _event_cache

    # Fast path — check cache without acquiring the lock first
    cache = _event_cache
    if cache is not None and (time.monotonic() - cache[1]) < _TTL_SECONDS:
        return cache[0]

    # Slow path — only one coroutine refreshes at a time
    async with _cache_lock:
        # Re-check after acquiring lock (another coroutine may have refreshed already)
        cache = _event_cache
        if cache is not None and (time.monotonic() - cache[1]) < _TTL_SECONDS:
            return cache[0]

        try:
            response = await (
                supabase_admin.table("events")
                .select("*")
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            event = Event(**response.data[0]) if response.data else None
        except Exception:
            return _event_cache[0] if _event_cache else None

        _event_cache = (event, time.monotonic())
        return event


async def get_event_by_id(event_id: str) -> Optional[Event]:
    """Fetches an event by its ID."""
    try:
        response = await (
            supabase_admin.table("events")
            .select("*")
            .eq("id", event_id)
            .single()
            .execute()
        )
        return Event(**response.data) if response.data else None
    except Exception:
        return None
