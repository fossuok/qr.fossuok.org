from fastapi import APIRouter, HTTPException
from services.registration import verify_registration

router: APIRouter = APIRouter(
    prefix="/api",
    tags=["API"]
)


@router.post("/verify")
async def api_verify(payload: dict):
    """
    Endpoint for QR code verification.
    Handles both the new per-registration QR format {rid, uid, eid}
    and the legacy per-user format {id, name, email, event}.
    Expects {"payload": "..."} where payload is the raw scanned string.
    """
    qr_data = payload.get("payload")
    if not qr_data:
        raise HTTPException(status_code=400, detail="No QR data provided")

    return await verify_registration(qr_data)
