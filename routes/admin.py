from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from routes.auth import get_current_user

router: APIRouter = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user=Depends(get_current_user)
):
    """Admin dashboard — requires GitHub login."""
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


@router.get("/verify", response_class=HTMLResponse)
async def admin_verify(
    request: Request,
    user=Depends(get_current_user)
):
    """QR code verification page — requires GitHub login."""
    return templates.TemplateResponse("verify.html", {"request": request, "user": user})
