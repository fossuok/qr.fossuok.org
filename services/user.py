import asyncio
import base64
import io
import json
import uuid

import qrcode
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from config.supabase import supabase
from schemas import CreateUser, VerifyUser
from .mail import send_qr_email


async def register_user(payload: CreateUser) -> JSONResponse:
    """
    Creates a new user record in Supabase and generates a QR code image.
    Sends the QR code via email.
    """
    new_id = str(uuid.uuid4())
    user_data = {
        "name": payload.name,
        "email": payload.email,
        "qr_code_data": new_id
    }

    # Supabase insertion
    try:
        # Using to_thread because supabase-py is sync
        await asyncio.to_thread(
            supabase.table("users").insert(user_data).execute
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")

    qr_payload = {"id": new_id, "name": payload.name, "email": payload.email}
    qr_data_url = generate_qr_data_url(json.dumps(qr_payload, separators=(",", ":")))

    # Send email asynchronously
    await send_qr_email(payload.email, payload.name, qr_data_url)

    return JSONResponse({
        "message": "User created and email sent",
        "id": new_id,
        "qr_data_url": qr_data_url,
    })


async def verify_user(payload: VerifyUser) -> dict:
    """
    Looks up a user in Supabase by their QR code data (UUID).
    """
    try:
        response = await asyncio.to_thread(
            supabase.table("users")
            .select("*")
            .eq("qr_code_data", payload.id)
            .execute
        )
        users = response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not users:
        raise HTTPException(status_code=404, detail="User not found")

    user = users[0]
    return {
        "valid": True,
        "user": {
            "id": user["qr_code_data"],
            "name": user["name"],
            "email": user["email"],
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
