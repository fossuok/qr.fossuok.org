import asyncio
import base64
import io
import json
import uuid
from datetime import datetime, timezone

import qrcode
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from config.supabase import supabase_admin
from schemas import CreateUser, VerifyUser
from .mail import send_qr_email


async def auto_register_user(supabase_user) -> dict:
    """
    Automatically registers a user upon GitHub login.
    Saves avatar, name, email, and links them to the active event.
    Returns the user data for session creation.
    """
    github_id = str(supabase_user.id)
    email = supabase_user.email
    name = supabase_user.user_metadata.get("full_name") or supabase_user.email
    avatar_url = supabase_user.user_metadata.get("avatar_url")

    # 1. Fetch active event
    from .event import get_active_event
    active_event = await get_active_event()
    event_id = active_event.id if active_event else None

    # 2. Check if user already exists
    try:
        existing = await asyncio.to_thread(
            supabase_admin.table("users")
            .select("*")
            .eq("github_id", github_id)
            .limit(1)
            .execute
        )
        user_record = existing.data[0] if existing.data else None
    except Exception:
        user_record = None

    if user_record:
        # Update info (avatar/name might change)
        update_data = {
            "name": name,
            "avatar_url": avatar_url,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        # If not registered for active event yet, link them
        if event_id and user_record.get("registered_event_id") != event_id:
            update_data["registered_event_id"] = event_id
        
        await asyncio.to_thread(
            supabase_admin.table("users").update(update_data).eq("github_id", github_id).execute
        )
        return {**user_record, **update_data}

    # 3. Completely New User
    new_qr_id = str(uuid.uuid4())
    new_user_data = {
        "github_id": github_id,
        "name": name,
        "email": email,
        "avatar_url": avatar_url,
        "qr_code_data": new_qr_id,
        "registered_event_id": event_id,
        "role": "participant"
    }

    try:
        res = await asyncio.to_thread(
            supabase_admin.table("users").insert(new_user_data).execute
        )
        created_user = res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    # 4. Generate QR and Email
    qr_payload = {
        "id": new_qr_id, 
        "name": name, 
        "email": email,
        "event": active_event.title if active_event else "FOSSUoK Event"
    }
    qr_data_url = generate_qr_data_url(json.dumps(qr_payload, separators=(",", ":")))
    
    # Email will be handled as a background task by the caller (auth route)
    # We return the email data along with the user record
    return {**created_user, "qr_data_url": qr_data_url}


async def verify_user(qr_input: str) -> dict:
    """
    Looks up a user in Supabase by their QR code data.
    The input can be a raw UUID string or a JSON string containing an 'id' key.
    """
    search_id = qr_input

    # Try to parse as JSON in case it's the full payload
    try:
        data = json.loads(qr_input)
        if isinstance(data, dict) and "id" in data:
            search_id = data["id"]
    except (json.JSONDecodeError, TypeError):
        # Not JSON, assume it's the raw ID string
        pass

    # Optimized: Only select needed columns
    try:
        response = await asyncio.to_thread(
            supabase_admin.table("users")
            .select("qr_code_data, name, email, attended_at")
            .eq("qr_code_data", search_id)
            .execute
        )
        users_list = response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not users_list:
        raise HTTPException(status_code=404, detail="User not found")

    user = users_list[0]
    attended_at = user.get("attended_at")
    already_marked = bool(attended_at)

    # 2. Update if not already marked
    if not already_marked:
        new_timestamp = datetime.now(timezone.utc).isoformat()
        # Fire and forget update to database for attendance (or wait and return updated)
        # We'll wait to ensure data consistency in the response
        await asyncio.to_thread(
            supabase_admin.table("users")
            .update({"attended_at": new_timestamp})
            .eq("qr_code_data", search_id)
            .execute
        )
        user["attended_at"] = new_timestamp

    return {
        "valid": True,
        "already_marked": already_marked,
        "user": {
            "id": user["qr_code_data"],
            "name": user["name"],
            "email": user["email"],
            "attended_at": user["attended_at"]
        },
    }


def get_qr_image(qr_data: str) -> StreamingResponse:
    """
    Generates a QR code PNG and streams it as a downloadable file.
    """
    buf = io.BytesIO()
    qrcode.make(qr_data).save(buf, format="PNG")
    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={qr_data}.png"}
    return StreamingResponse(buf, media_type="image/png", headers=headers)


def generate_qr_data_url(text: str) -> str:
    """Encodes a QR code as a base64 PNG data URL."""
    buf = io.BytesIO()
    qrcode.make(text).save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"
