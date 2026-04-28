import asyncio
import base64
import io
import json
import time
import uuid
from datetime import datetime, timezone

import qrcode
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from repository.user_repo import (
    get_user_by_github_id, update_user_by_github_id, create_user,
    get_user_by_qr_code, update_user_by_qr_code
)
from repository.event_repo import get_active_event_dict

_profile_cache: dict[str, tuple[dict | None, float]] = {}
_PROFILE_TTL: int = 300  # 5 minutes


def invalidate_user_profile_cache(qr_code_data: str) -> None:
    _profile_cache.pop(qr_code_data, None)


async def auto_register_user(supabase_user) -> dict:
    """
    Automatically registers a user upon GitHub login.
    """
    github_id = str(supabase_user.id)
    email = supabase_user.email
    name = supabase_user.user_metadata.get("full_name") or supabase_user.email
    avatar_url = supabase_user.user_metadata.get("avatar_url")

    # Fetch existing user only
    user_record = await get_user_by_github_id(github_id)

    if user_record:
        update_data = {}
        if user_record.get("name") != name:
            update_data["name"] = name
        if user_record.get("avatar_url") != avatar_url:
            update_data["avatar_url"] = avatar_url

        async def _bg_update():
            try:
                from services.event import _active_event_cache
                cached_event = _active_event_cache.get("data")
                if cached_event and user_record.get("registered_event_id") != cached_event.id:
                    update_data["registered_event_id"] = cached_event.id

                if update_data:
                    await update_user_by_github_id(github_id, update_data)
            except Exception:
                pass

        asyncio.create_task(_bg_update())

        return {**user_record, **update_data}

    # Completely new user
    new_qr_id = str(uuid.uuid4())
    new_user_data = {
        "github_id": github_id,
        "name": name,
        "email": email,
        "avatar_url": avatar_url,
        "qr_code_data": new_qr_id,
        "role": "participant",
    }

    try:
        created_user = await create_user(new_user_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    # For new users, we fetch the event to generate their first QR code
    active_event = await get_active_event_dict()
    event_id = active_event["id"] if active_event else None

    if event_id:
        try:
            await update_user_by_github_id(github_id, {"registered_event_id": event_id})
        except Exception:
            pass

    # Generate QR (CPU-bound) in a thread so it doesn't block the event loop
    qr_payload = {
        "id": new_qr_id,
        "name": name,
        "email": email,
        "event": active_event["title"] if active_event else "FOSSUoK Event",
    }
    qr_data_url = await asyncio.to_thread(
        generate_qr_data_url, json.dumps(qr_payload, separators=(",", ":"))
    )

    return {**created_user, "qr_data_url": qr_data_url}


async def verify_user(qr_input: str) -> dict:
    """Legacy user-level QR verification. See registration.py for event-level."""
    search_id = qr_input

    try:
        data = json.loads(qr_input)
        if isinstance(data, dict) and "id" in data:
            search_id = data["id"]
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        user = await get_user_by_qr_code(search_id, select="qr_code_data, name, email, attended_at")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    attended_at = user.get("attended_at")
    already_marked = bool(attended_at)

    if not already_marked:
        new_timestamp = datetime.now(timezone.utc).isoformat()

        # Fire-and-forget
        async def _update_attendance():
            try:
                await update_user_by_qr_code(search_id, {"attended_at": new_timestamp})
            except Exception:
                pass

        asyncio.create_task(_update_attendance())
        attended_at = new_timestamp

    return {
        "valid": True,
        "already_marked": already_marked,
        "user": {
            "id": user["qr_code_data"],
            "name": user["name"],
            "email": user["email"],
            "attended_at": attended_at,
        },
    }


def get_qr_image(qr_data: str) -> StreamingResponse:
    buf = io.BytesIO()
    qrcode.make(qr_data).save(buf, format="PNG")
    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={qr_data}.png"}
    return StreamingResponse(buf, media_type="image/png", headers=headers)


def generate_qr_data_url(text: str) -> str:
    buf = io.BytesIO()
    qrcode.make(text).save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


async def get_user_profile(qr_code_data: str) -> dict | None:
    cached = _profile_cache.get(qr_code_data)
    if cached is not None and (time.monotonic() - cached[1]) < _PROFILE_TTL:
        return cached[0]

    try:
        profile = await get_user_by_qr_code(qr_code_data, select="qr_code_data, participant_type, email, name, avatar_url")
    except Exception:
        return _profile_cache.get(qr_code_data, (None,))[0]

    _profile_cache[qr_code_data] = (profile, time.monotonic())
    return profile


async def complete_user_profile(qr_code_data: str, profile_data: dict) -> None:
    ptype = profile_data["participant_type"]
    update = {
        "participant_type": ptype,
        "student_id": profile_data.get("student_id"),
        "university": "University of Kelaniya" if ptype == "uok_student" else profile_data.get("university"),
        "study_year": profile_data.get("study_year"),
        "organization": profile_data.get("organization"),
        "job_role": profile_data.get("job_role"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await update_user_by_qr_code(qr_code_data, update)
    invalidate_user_profile_cache(qr_code_data)
