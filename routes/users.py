from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import get_db
from schemas import CreateUser, VerifyUser
from services import register_user, get_qr_image

router: APIRouter = APIRouter(
    prefix="/user",
    tags=["User"]
)

templates = Jinja2Templates(directory="templates")
db_dep = Annotated[Session, Depends(get_db)]


@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request):
    """Public event listing — users pick an event and register."""
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    """User dashboard — placeholder for future user session support."""
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/events/register")
async def api_register(payload: CreateUser, db: db_dep):
    """Register a user for an event and return their QR code."""
    try:
        return register_user(payload, db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events/{qr_data}/qr")
async def download_qr(qr_data: str):
    """Stream a QR code PNG for the given data string as a file download."""
    try:
        return get_qr_image(qr_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
