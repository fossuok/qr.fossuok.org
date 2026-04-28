import asyncio
import base64
import io
import json
import uuid
from datetime import datetime, timezone

import qrcode
from cachetools import TTLCache
from fastapi import HTTPException

from repository.event_repo import get_all_active_events as get_active_events_repo, get_event_by_id
from repository.registration_repo import (
    get_user_registrations as get_user_registrations_repo,
    create_registration, get_registration_by_id, update_registration
)
from repository.user_repo import get_user_by_qr_code, update_user_by_qr_code

_active_events_cache = TTLCache(maxsize=1, ttl=120)  # 2 minutes


def invalidate_active_events_cache() -> None:
    _active_events_cache.clear()


async def get_user_registrations(user_qr_code: str) -> list[dict]:
    return await get_user_registrations_repo(user_qr_code)


async def get_all_active_events() -> list[dict]:
    if "data" in _active_events_cache:
        return _active_events_cache["data"]

    try:
        result = await get_active_events_repo()
    except Exception:
        return _active_events_cache.get("data", [])

    _active_events_cache["data"] = result
    return result


async def register_for_event(
        user_qr_code: str,
        event_id: str,
        user_name: str,
        user_email: str,
) -> dict:
    reg_id = str(uuid.uuid4())

    try:
        registration = await create_registration({
            "id": reg_id, 
            "user_qr_code": user_qr_code, 
            "event_id": event_id
        })
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            raise HTTPException(status_code=409, detail="Already registered for this event.")
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    try:
        event = await get_event_by_id(event_id, select="title")
        event_title = event.get("title", "FOSSUoK Event") if event else "FOSSUoK Event"
    except Exception:
        event_title = "FOSSUoK Event"

    qr_payload = json.dumps(
        {"rid": reg_id, "uid": user_qr_code, "eid": event_id, "name": user_name, "event": event_title},
        separators=(",", ":"),
    )
    qr_data_url = await asyncio.to_thread(_generate_qr_data_url, qr_payload)

    return {**registration, "qr_data_url": qr_data_url, "event_title": event_title}


async def get_registration_qr_payload(registration_id: str, user_qr_code: str) -> str | None:
    try:
        reg = await get_registration_by_id(registration_id, select="id, user_qr_code, event_id", user_qr_code=user_qr_code)
        if not reg:
            return None

        event_task = get_event_by_id(reg["event_id"], select="title")
        user_task = get_user_by_qr_code(user_qr_code, select="name")
        event, user = await asyncio.gather(event_task, user_task)

        event_title = event.get("title", "FOSSUoK Event") if event else "FOSSUoK Event"
        user_name = user.get("name", "") if user else ""

        return json.dumps(
            {"rid": reg["id"], "uid": reg["user_qr_code"], "eid": reg["event_id"],
             "name": user_name, "event": event_title},
            separators=(",", ":"),
        )
    except Exception:
        return None


async def verify_registration(qr_raw: str) -> dict:
    try:
        data = json.loads(qr_raw)
    except (json.JSONDecodeError, TypeError):
        data = {"id": qr_raw}

    if "rid" in data:
        reg_id = data["rid"]
        try:
            reg = await get_registration_by_id(reg_id, select="id, user_qr_code, event_id, attended_at")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found.")

        user_task = get_user_by_qr_code(reg["user_qr_code"], select="name, email, avatar_url")
        event_task = get_event_by_id(reg["event_id"], select="id, title")
        
        user_dict, event_dict = await asyncio.gather(user_task, event_task)

        already_marked = bool(reg.get("attended_at"))
        attended_at = reg.get("attended_at")

        if not already_marked:
            attended_at = datetime.now(timezone.utc).isoformat()

            async def _mark():
                try:
                    await update_registration(reg_id, {"attended_at": attended_at})
                except Exception:
                    pass

            asyncio.create_task(_mark())

        u = user_dict or {}
        e = event_dict or {}

        return {
            "valid": True,
            "already_marked": already_marked,
            "format": "registration",
            "user": {
                "id": reg["user_qr_code"],
                "name": u.get("name", "Unknown"),
                "email": u.get("email", ""),
                "avatar_url": u.get("avatar_url"),
                "attended_at": attended_at,
            },
            "event": {"id": reg["event_id"], "title": e.get("title", "—")},
        }

    # Legacy format
    search_id = data.get("id", qr_raw)
    try:
        user = await get_user_by_qr_code(search_id, select="qr_code_data, name, email, attended_at")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    already_marked = bool(user.get("attended_at"))
    attended_at = user.get("attended_at")

    if not already_marked:
        attended_at = datetime.now(timezone.utc).isoformat()

        async def _mark_legacy():
            try:
                await update_user_by_qr_code(search_id, {"attended_at": attended_at})
            except Exception:
                pass

        asyncio.create_task(_mark_legacy())

    return {
        "valid": True,
        "already_marked": already_marked,
        "format": "legacy",
        "user": {
            "id": user["qr_code_data"],
            "name": user["name"],
            "email": user["email"],
            "attended_at": attended_at,
        },
        "event": None,
    }


def _generate_qr_data_url(text: str) -> str:
    buf = io.BytesIO()
    qrcode.make(text).save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"
