import asyncio

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from services import get_qr_image
from routes.auth import get_current_user

router: APIRouter = APIRouter(
    prefix="/user",
    tags=["User"]
)

templates = Jinja2Templates(directory="templates")


@router.get("/registration-success", response_class=HTMLResponse)
async def registration_success(
    request: Request,
    user=Depends(get_current_user)
):
    """
    Shows a success message after automatic registration.
    """
    from services.user import generate_qr_data_url
    # generate_qr_data_url is CPU-bound (qrcode.make); offload to a thread pool
    qr_url = await asyncio.to_thread(generate_qr_data_url, user.user_id)
    
    return templates.TemplateResponse("success.html", {
        "request": request,
        "user": user,
        "qr_data_url": qr_url,
        "status": "Verified & Registered"
    })


@router.get("/events/{qr_data}/qr")
async def download_qr(qr_data: str):
    """Stream a QR code PNG for the given data string as a file download."""
    try:
        return get_qr_image(qr_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
