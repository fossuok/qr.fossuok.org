import base64
import io
import json
import uuid

import qrcode
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from models import User
from schemas import CreateUser, VerifyUser


def register_user(payload: CreateUser, db: Session) -> JSONResponse:
    """
    Creates a new user record and generates a QR code image.
    Returns the user id and QR code as a base64 data URL.
    """
    new_id = str(uuid.uuid4())
    new_user = User(**payload.model_dump(), qr_code_data=new_id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    qr_payload = {"id": new_id, "name": payload.name, "email": payload.email}
    qr_data_url = generate_qr_data_url(json.dumps(qr_payload, separators=(",", ":")))

    return JSONResponse({
        "message": "User created",
        "id": new_id,
        "qr_data_url": qr_data_url,
    })


def verify_user(payload: VerifyUser, db: Session) -> dict:
    """
    Looks up a user by their QR code data (UUID).
    Returns the user details if found, raises 404 if not.
    """
    user = db.query(User).filter(User.qr_code_data == payload.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "valid": True,
        "user": {
            "id": user.qr_code_data,
            "name": user.name,
            "email": user.email,
        },
    }


def get_qr_image(qr_data: str) -> StreamingResponse:
    """
    Generates a QR code PNG for the given data string and streams it
    as a downloadable file attachment.
    """
    buf = io.BytesIO()
    qrcode.make(qr_data).save(buf, format="PNG")
    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={qr_data}.png"}
    return StreamingResponse(buf, media_type="image/png", headers=headers)


def generate_qr_data_url(text: str) -> str:
    """Encodes a QR code for `text` as a base64 PNG data URL."""
    buf = io.BytesIO()
    qrcode.make(text).save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"
