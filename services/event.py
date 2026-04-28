from typing import Optional

from cachetools import TTLCache
from starlette.datastructures import FormData

from schema.event import Event
from repository.event_repo import (
    get_active_event_dict, get_event_by_id as get_event_by_id_repo,
    get_all_events as get_all_events_repo, create_event, update_event,
    delete_event, deactivate_all_active_events_except
)
from repository.user_repo import nullify_registered_event_id

_active_event_cache = TTLCache(maxsize=1, ttl=300)  # 5 minutes
_all_events_cache = TTLCache(maxsize=1, ttl=60)  # 1 minute

# Import inside function to avoid circular import if needed
def invalidate_event_cache() -> None:
    _active_event_cache.clear()
    _all_events_cache.clear()
    from services.registration import invalidate_active_events_cache
    invalidate_active_events_cache()


async def get_active_event() -> Optional[Event]:
    if "data" in _active_event_cache:
        return _active_event_cache["data"]

    try:
        event_dict = await get_active_event_dict()
        event = Event(**event_dict) if event_dict else None
    except Exception:
        return _active_event_cache.get("data")

    _active_event_cache["data"] = event
    return event


async def get_event_by_id(event_id: str) -> Optional[Event]:
    try:
        event_dict = await get_event_by_id_repo(event_id)
        return Event(**event_dict) if event_dict else None
    except Exception:
        return None


async def get_all_events():
    if "data" in _all_events_cache:
        return _all_events_cache["data"]

    try:
        events_list = await get_all_events_repo()
    except Exception:
        return _all_events_cache.get("data", [])

    _all_events_cache["data"] = events_list
    return events_list


async def add_event(form: FormData):
    event_data: dict = {
        "title": form.get("title"),
        "description": form.get("description") or None,
        "location": form.get("location") or None,
        "start_time": form.get("start_time") or None,
        "end_time": form.get("end_time") or None,
        "image_url": form.get("image_url") or None,
        "whatsapp_link": form.get("whatsapp_link") or None,
        "is_active": form.get("is_active") == "on",
    }

    if not event_data["title"]:
        return "Title is required", False, 400

    try:
        if event_data["is_active"]:
            await deactivate_all_active_events_except(None)

        await create_event(event_data)
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
        "whatsapp_link": form.get("whatsapp_link") or None,
        "is_active": form.get("is_active") == "on",
    }

    if not update_data["title"]:
        return "Title is required", False, 400

    try:
        if update_data["is_active"]:
            await deactivate_all_active_events_except(event_id)

        await update_event(event_id, update_data)
        invalidate_event_cache()
        return None, True, 200
    except Exception as e:
        return f"Failed to create event: {str(e)}", False, 500


async def toggle_event_status(event_id: str):
    try:
        event_dict = await get_event_by_id_repo(event_id, select="is_active")
        current_active = event_dict.get("is_active", False) if event_dict else False
        new_active = not current_active

        if new_active:
            await deactivate_all_active_events_except(event_id)

        await update_event(event_id, {"is_active": new_active})
        invalidate_event_cache()
    except Exception as e:
        return str(e), False

    status = "activated" if new_active else "deactivated"
    return status, True


async def delete_event_data(event_id: str):
    try:
        await nullify_registered_event_id(event_id)
        await delete_event(event_id)
        invalidate_event_cache()
        return None, True
    except Exception as e:
        return str(e), False
