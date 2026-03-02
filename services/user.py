import asyncio
import base64
import io
import json
import uuid
from datetime import datetime, timezone

import qrcode
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from config.supabase import supabase_admin
from .event import get_active_event


async def auto_register_user(supabase_user) -> dict:
    """
    Automatically registers a user upon GitHub login.
    Uses the persistent async Supabase client — no per-call connection overhead.
    Event fetch and user-existence check run in parallel via asyncio.gather.
    """
    github_id = str(supabase_user.id)
    email = supabase_user.email
    name = supabase_user.user_metadata.get("full_name") or supabase_user.email
    avatar_url = supabase_user.user_metadata.get("avatar_url")

    async def _fetch_existing_user():
        try:
            res = await (
                supabase_admin.table("users")
                .select("github_id, name, email, avatar_url, qr_code_data, role, registered_event_id, attended_at")
                .eq("github_id", github_id)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception:
            return None

    # Run event fetch and user lookup in parallel
    active_event, user_record = await asyncio.gather(
        get_active_event(),
        _fetch_existing_user(),
    )

    event_id = active_event.id if active_event else None

    if user_record:
        update_data = {
            "name": name,
            "avatar_url": avatar_url,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if event_id and user_record.get("registered_event_id") != event_id:
            update_data["registered_event_id"] = event_id

        # Fire-and-forget: the response only needs the merged dict,
        # not the DB write to be confirmed.  Saves ~300ms.
        async def _bg_update():
            try:
                await (
                    supabase_admin.table("users")
                    .update(update_data)
                    .eq("github_id", github_id)
                    .execute()
                )
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
        "registered_event_id": event_id,
        "role": "participant",
    }

    try:
        res = await supabase_admin.table("users").insert(new_user_data).execute()
        created_user = res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    # Generate QR (CPU-bound) in a thread so it doesn't block the event loop
    qr_payload = {
        "id": new_qr_id,
        "name": name,
        "email": email,
        "event": active_event.title if active_event else "FOSSUoK Event",
    }
    qr_data_url = await asyncio.to_thread(
        generate_qr_data_url, json.dumps(qr_payload, separators=(",", ":"))
    )

    return {**created_user, "qr_data_url": qr_data_url}


async def verify_user(qr_input: str) -> dict:
    """
    Looks up a user by their QR code data and marks attendance.
    The attendance UPDATE is fire-and-forget so the response returns immediately.
    Uses the persistent async Supabase client — no per-call connection overhead.
    """
    search_id = qr_input

    try:
        data = json.loads(qr_input)
        if isinstance(data, dict) and "id" in data:
            search_id = data["id"]
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        response = await (
            supabase_admin.table("users")
            .select("qr_code_data, name, email, attended_at")
            .eq("qr_code_data", search_id)
            .limit(1)
            .execute()
        )
        users_list = response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not users_list:
        raise HTTPException(status_code=404, detail="User not found")

    user = users_list[0]
    attended_at = user.get("attended_at")
    already_marked = bool(attended_at)

    if not already_marked:
        new_timestamp = datetime.now(timezone.utc).isoformat()

        # Fire-and-forget: return the response immediately
        async def _update_attendance():
            try:
                await (
                    supabase_admin.table("users")
                    .update({"attended_at": new_timestamp})
                    .eq("qr_code_data", search_id)
                    .execute()
                )
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
    """Generates a QR code PNG and streams it as a downloadable file."""
    buf = io.BytesIO()
    qrcode.make(qr_data).save(buf, format="PNG")
    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={qr_data}.png"}
    return StreamingResponse(buf, media_type="image/png", headers=headers)


def generate_qr_data_url(text: str) -> str:
    """Encodes a QR code as a base64 PNG data URL. CPU-bound — call via asyncio.to_thread."""
    buf = io.BytesIO()
    qrcode.make(text).save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"
