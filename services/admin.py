import asyncio
from datetime import datetime, timezone

from fpdf import FPDF

from config.supabase import supabase_admin


# user management
async def fetch_user_stat():
    # Fetch stats concurrently using the persistent async Supabase client
    try:
        res_reg_task = supabase_admin.table("users").select("id", count="exact").execute()
        res_att_task = supabase_admin.table("users").select("id", count="exact").not_.is_("attended_at",
                                                                                          "null").execute()

        res_reg, res_att = await asyncio.gather(res_reg_task, res_att_task)

        total_registered = res_reg.count or 0
        total_attended = res_att.count or 0
    except Exception:
        total_registered = 0
        total_attended = 0

    return total_registered, total_attended


async def get_all_participants():
    # Fetch all participants using the persistent async Supabase client
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
    return users


async def get_all_users():
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

    return users_list


async def change_user_role(github_id: str, role: str = "admin"):
    try:
        await (
            supabase_admin.table("users")
            .update({"role": role})
            .eq("github_id", github_id)
            .execute()
        )
        return None, True
    except Exception as e:
        return e, False


async def delete_user_from_db(github_id: str):
    try:
        await (
            supabase_admin.table("users")
            .delete()
            .eq("github_id", github_id)
            .execute()
        )
        return None, True
    except Exception as e:
        return e, False


def generate_pdf(users):
    # Create PDF
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
            pdf.set_text_color(40, 167, 69)  # Success Green
        else:
            pdf.set_text_color(220, 53, 69)  # Danger Red

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

    # Output as stream
    pdf_output = pdf.output(dest='S')
    return pdf_output