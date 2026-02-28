from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fpdf import FPDF
import io
from datetime import datetime, timezone

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
        # Fetch stats concurrently using the persistent async Supabase client
        res_reg_task = supabase_admin.table("users").select("id", count="exact").execute()
        res_att_task = supabase_admin.table("users").select("id", count="exact").not_.is_("attended_at", "null").execute()
        
        res_reg, res_att = await asyncio.gather(res_reg_task, res_att_task)
        
        total_registered = res_reg.count or 0
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


@router.get("/export-attendance")
async def export_attendance(
        user=Depends(get_current_user)
):
    """Generates and streams a styled PDF attendance report."""
    from config.supabase import supabase_admin

    # 1. Fetch all participants using the persistent async Supabase client
    try:
        res = await (
            supabase_admin.table("users")
            .select("name, email, role, attended_at")
            .eq("role", "participant")
            .order("name")
            .execute()
        )
        users = res.data or []
    except Exception:
        users = []

    # 2. Create PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(75, 46, 131)  # FOSSUOK Purple
    pdf.cell(0, 15, "Attendance Report", ln=True, align="C")
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True, align="C")
    pdf.ln(10)

    # Table Header
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(75, 46, 131)
    pdf.set_text_color(255, 255, 255)
    
    cols = [("Name", 60), ("Email", 70), ("Role", 30), ("Status", 30)]
    for col_name, width in cols:
        pdf.cell(width, 10, col_name, border=1, align="C", fill=True)
    pdf.ln()

    # Table Rows
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    
    fill = False
    for u in users:
        # Zebra striping
        pdf.set_fill_color(245, 245, 245)
        
        name = str(u.get("name", "N/A"))[:30]
        email = str(u.get("email", "N/A"))[:35]
        role = str(u.get("role", "participant")).capitalize()
        status = "Present" if u.get("attended_at") else "Absent"
        
        # Adjusting font color for status
        pdf.set_font("Arial", "B" if status == "Present" else "", 10)
        if status == "Present":
            pdf.set_text_color(40, 167, 69) # Success Green
        else:
            pdf.set_text_color(220, 53, 69) # Danger Red

        # We actually need to reset text color for other columns
        h = 8
        pdf.cell(60, h, name, border=1, fill=fill)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.cell(70, h, email, border=1, fill=fill)
        pdf.cell(30, h, role, border=1, fill=fill)
        
        # Status again
        pdf.set_font("Arial", "B" if status == "Present" else "", 10)
        if status == "Present":
            pdf.set_text_color(40, 167, 69)
        else:
            pdf.set_text_color(220, 53, 69)
        pdf.cell(30, h, status, border=1, fill=fill, align="C")
        
        pdf.set_text_color(0, 0, 0)
        pdf.ln()
        fill = not fill

    # 3. Output as stream
    pdf_output = pdf.output(dest='S')
    
    return StreamingResponse(
        io.BytesIO(pdf_output),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
    )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
        request: Request,
        user=Depends(get_current_user)
):
    """Admin page — lists all registered users with their roles."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from config.supabase import supabase_admin

    try:
        res = await (
            supabase_admin.table("users")
            .select("github_id, name, email, avatar_url, role, created_at")
            .order("role")
            .order("created_at", desc=True)
            .execute()
        )
        users_list = res.data or []
    except Exception:
        users_list = []

    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "user": user,
        "users_list": users_list,
    })


@router.post("/users/{github_id}/promote")
async def promote_user(
        github_id: str,
        user=Depends(get_current_user)
):
    """Promote a user to admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from config.supabase import supabase_admin

    try:
        await (
            supabase_admin.table("users")
            .update({"role": "admin"})
            .eq("github_id", github_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to promote user: {str(e)}")

    return RedirectResponse(url="/admin/users?success=promoted", status_code=303)


@router.post("/users/{github_id}/demote")
async def demote_user(
        github_id: str,
        user=Depends(get_current_user)
):
    """Demote an admin back to participant role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from config.supabase import supabase_admin

    try:
        await (
            supabase_admin.table("users")
            .update({"role": "participant"})
            .eq("github_id", github_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to demote user: {str(e)}")

    return RedirectResponse(url="/admin/users?success=demoted", status_code=303)


@router.post("/users/{github_id}/delete")
async def delete_user(
        github_id: str,
        user=Depends(get_current_user)
):
    """Delete a user from the system."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from config.supabase import supabase_admin

    try:
        await (
            supabase_admin.table("users")
            .delete()
            .eq("github_id", github_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

    return RedirectResponse(url="/admin/users?success=deleted", status_code=303)

