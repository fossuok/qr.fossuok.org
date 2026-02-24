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
    """Admin dashboard — shows event stats."""
    from config.supabase import supabase_admin
    import asyncio
    
    try:
        # Get total registered
        res_reg = await asyncio.to_thread(
            supabase_admin.table("users").select("id", count="exact").execute
        )
        total_registered = res_reg.count or 0
        
        # Get total attended (not null attended_at)
        res_att = await asyncio.to_thread(
            supabase_admin.table("users").select("id", count="exact").not_.is_("attended_at", "null").execute
        )
        total_attended = res_att.count or 0
    except Exception:
        total_registered = 0
        total_attended = 0

    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user,
        "stats": {
            "total_registered": total_registered,
            "total_attended": total_attended,
            "attendance_rate": round((total_attended / total_registered * 100), 1) if total_registered > 0 else 0
        }
    })


@router.get("/verify", response_class=HTMLResponse)
async def admin_verify(
        request: Request,
        user=Depends(get_current_user)
):
    """QR code verification page — requires GitHub login."""
    return templates.TemplateResponse("verify.html", {"request": request, "user": user})
