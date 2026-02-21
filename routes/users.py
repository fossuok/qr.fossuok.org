from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import get_db
from schemas import CreateUser, VerifyUser
from services import register_user, verify_user, get_qr_image

router = APIRouter()
templates = Jinja2Templates(directory="templates")

db_dep = Annotated[Session, Depends(get_db)]


@router.get("/", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request):
    return templates.TemplateResponse("verify.html", {"request": request})


@router.post("/api/register")
async def api_register(payload: CreateUser, db: db_dep):
    """Register a new user and return their generated QR code."""
    try:
        return register_user(payload, db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{qr_data}/qr")
async def download_qr(qr_data: str):
    """Stream a QR code PNG for the given data string as a file download."""
    try:
        return get_qr_image(qr_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/verify")
async def api_verify(payload: VerifyUser, db: db_dep):
    """Verify a scanned QR code and return the associated user details."""
    try:
        return verify_user(payload, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
