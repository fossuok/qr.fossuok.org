from fastapi import APIRouter, HTTPException
from schemas import VerifyUser
from services import verify_user

router: APIRouter = APIRouter(
    prefix="/api",
    tags=["API"]
)

@router.post("/verify")
async def api_verify(payload: dict):
    """
    Endpoint for QR code verification.
    Expects {"payload": "..."} where payload is the scanned string.
    """
    # Extract the scanned string from the frontend's 'payload' key
    qr_data = payload.get("payload")
    if not qr_data:
        raise HTTPException(status_code=400, detail="No QR data provided")

    # Pass the raw data to the service which will handle parsing
    return await verify_user(qr_data)
