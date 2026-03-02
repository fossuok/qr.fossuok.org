import asyncio
import time
from typing import Optional

from starlette.datastructures import FormData

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


async def get_all_events():
    try:
        res = await (
            supabase_admin.table("events")
            .select("*")
            .order("is_active", desc=True)
            .order("created_at", desc=True)
            .execute()
        )
        events_list = res.data or []
    except Exception:
        events_list = []

    return events_list


async def add_event(form: FormData):
    event_data: dict = {
        "title": form.get("title"),
        "description": form.get("description") or None,
        "location": form.get("location") or None,
        "start_time": form.get("start_time") or None,
        "end_time": form.get("end_time") or None,
        "image_url": form.get("image_url") or None,
        "is_active": form.get("is_active") == "on",
    }

    if not event_data["title"]:
        return "Title is required", False, 400

    try:
        # If activating this event, deactivate all others first
        if event_data["is_active"]:
            await (
                supabase_admin.table("events")
                .update({"is_active": False})
                .eq("is_active", True)
                .execute()
            )

        await supabase_admin.table("events").insert(event_data).execute()
        invalidate_event_cache()
        return None, True, 200
    except Exception as e:
        return f"Failed to create event: {str(e)}", False, 500


async def update_event_data(form: FormData, event_id: str):
    update_data = {
        "title": form.get("title"),
        "description": form.get("description") or None,
        "location": form.get("location") or None,
        "start_time": form.get("start_time") or None,
        "end_time": form.get("end_time") or None,
        "image_url": form.get("image_url") or None,
        "is_active": form.get("is_active") == "on",
    }

    if not update_data["title"]:
        return "Title is required", False, 400

    try:
        # If activating this event, deactivate all others first
        if update_data["is_active"]:
            await (
                supabase_admin.table("events")
                .update({"is_active": False})
                .neq("id", event_id)
                .eq("is_active", True)
                .execute()
            )

        await (
            supabase_admin.table("events")
            .update(update_data)
            .eq("id", event_id)
            .execute()
        )
        invalidate_event_cache()
        return None, True, 200
    except Exception as e:
        return f"Failed to create event: {str(e)}", False, 500


async def toggle_event_status(event_id: str):
    try:
        # Get current status
        res = await (
            supabase_admin.table("events")
            .select("is_active")
            .eq("id", event_id)
            .single()
            .execute()
        )
        current_active = res.data.get("is_active", False)
        new_active = not current_active

        if new_active:
            # Deactivate all others first
            await (
                supabase_admin.table("events")
                .update({"is_active": False})
                .eq("is_active", True)
                .execute()
            )

        await (
            supabase_admin.table("events")
            .update({"is_active": new_active})
            .eq("id", event_id)
            .execute()
        )
        invalidate_event_cache()
    except Exception as e:
        return str(e), False

    status = "activated" if new_active else "deactivated"
    return status, True


async def delete_event_data(event_id: str):
    try:
        await (
            supabase_admin.table("events")
            .delete()
            .eq("id", event_id)
            .execute()
        )
        invalidate_event_cache()
        return None, True
    except Exception as e:
        return str(e), False
