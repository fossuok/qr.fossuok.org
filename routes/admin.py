from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
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


@router.get("/export-attendance")
async def export_attendance(
        user=Depends(get_current_user)
):
    """Generates and streams a styled PDF attendance report."""
    from config.supabase import supabase_admin
    import asyncio

    # 1. Fetch all participants
    try:
        res = await asyncio.to_thread(
            supabase_admin.table("users")
            .select("*")
            .eq("role", "participant")
            .order("name")
            .execute
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
