import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from cachetools import TTLCache
from fpdf import FPDF

from repository.user_repo import (
    get_registered_participant_count, get_all_participants as get_all_participants_repo,
    get_users_by_qr_codes, get_paginated_users as get_paginated_users_repo,
    update_user_by_github_id, delete_user_by_github_id, get_user_by_github_id
)
from repository.registration_repo import (
    get_attended_count, get_all_registrations, get_registrations_for_event,
    delete_registrations_for_user
)
from repository.event_repo import get_event_by_id

_stat_cache = TTLCache(maxsize=1, ttl=60)  # 1 minute
_paginated_users_cache = TTLCache(maxsize=50, ttl=30)  # 30 seconds only


async def fetch_user_stat():
    if "data" in _stat_cache:
        return _stat_cache["data"]

    try:
        reg_task = get_registered_participant_count()
        att_task = get_attended_count()
        total_registered, total_attended = await asyncio.gather(reg_task, att_task)
    except Exception:
        return _stat_cache.get("data", (0, 0))

    result = (total_registered, total_attended)
    _stat_cache["data"] = result
    return result


def invalidate_stat_cache() -> None:
    _stat_cache.clear()


async def get_all_participants():
    try:
        users_task = get_all_participants_repo()
        reg_task = get_all_registrations(select="user_qr_code, attended_at")
        users, registrations = await asyncio.gather(users_task, reg_task)
    except Exception:
        return []

    reg_count: dict = defaultdict(int)
    att_count: dict = defaultdict(int)
    for r in registrations:
        reg_count[r["user_qr_code"]] += 1
        if r["attended_at"]:
            att_count[r["user_qr_code"]] += 1

    return [
        {
            **u,
            "events_registered": reg_count[u["qr_code_data"]],
            "events_attended": att_count[u["qr_code_data"]],
            "attended_at": att_count[u["qr_code_data"]] > 0,
        }
        for u in users
    ]


async def get_participants_for_event(event_id: str):
    try:
        event_task = get_event_by_id(event_id, select="id, title")
        reg_task = get_registrations_for_event(event_id)
        event, registrations = await asyncio.gather(event_task, reg_task)
    except Exception:
        return [], None

    if not registrations:
        return [], event

    user_qr_codes = [r["user_qr_code"] for r in registrations]
    try:
        users_res = await get_users_by_qr_codes(user_qr_codes, select="qr_code_data, name, email, role, participant_type, student_id, university, organization, job_role")
        users_by_qr = {u["qr_code_data"]: u for u in users_res}
    except Exception:
        users_by_qr = {}

    participants = []
    for reg in registrations:
        user = users_by_qr.get(reg["user_qr_code"], {})
        participants.append({**user, "attended_at": reg["attended_at"], "registered_at": reg["registered_at"]})

    return participants, event


async def get_paginated_users(page: int = 1, limit: int = 15, search: str = "") -> dict:
    cache_key = (page, limit, search.lower().strip())

    if cache_key in _paginated_users_cache:
        return _paginated_users_cache[cache_key]

    offset = (page - 1) * limit
    users, total = await get_paginated_users_repo(offset, limit, search)

    result = {
        "users": users,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": -(-total // limit) if total > 0 else 1
    }

    _paginated_users_cache[cache_key] = result
    return result


def invalidate_users_cache() -> None:
    _paginated_users_cache.clear()


async def change_user_role(github_id: str, role: str = "admin"):
    try:
        await update_user_by_github_id(github_id, {"role": role})
        return None, True
    except Exception as e:
        return e, False


async def delete_user_from_db(github_id: str):
    try:
        user = await get_user_by_github_id(github_id)
        qr_code_data = user.get("qr_code_data") if user else None

        if qr_code_data:
            await delete_registrations_for_user(qr_code_data)

        await delete_user_by_github_id(github_id)
        return None, True
    except Exception as e:
        return str(e), False


def generate_pdf(participants, event_title: str = "All Events", per_event: bool = False):
    pdf = FPDF()
    pdf.add_page()

    # ── Header ──────────────────────────────────────────────────────────────
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(75, 46, 131)
    pdf.cell(0, 15, "Attendance Report", ln=True, align="C")

    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(75, 46, 131)
    pdf.cell(0, 8, event_title, ln=True, align="C")

    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True, align="C")
    pdf.ln(8)

    h = 8

    if per_event:
        # ── Per-event: Name | Email | Affiliation | Status ──────────────────
        cols = [("Name", 50), ("Email", 60), ("Affiliation", 50), ("Status", 30)]
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(75, 46, 131)
        pdf.set_text_color(255, 255, 255)
        for col_name, width in cols:
            pdf.cell(width, 10, col_name, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        fill = False
        for p in participants:
            pdf.set_fill_color(245, 245, 245)
            name = str(p.get("name", "N/A"))[:28]
            email = str(p.get("email", "N/A"))[:32]

            ptype = p.get("participant_type", "")
            if ptype == "uok_student":
                affil = f"UoK | {p.get('student_id', '')}"
            elif ptype == "other_university":
                affil = str(p.get("university", ""))[:22]
            elif ptype == "industry":
                affil = f"{p.get('organization', '')} | {p.get('job_role', '')}"[:22]
            else:
                affil = "—"

            status = "Present" if p.get("attended_at") else "Absent"
            s_color = (40, 167, 69) if status == "Present" else (220, 53, 69)

            pdf.set_text_color(0, 0, 0)
            pdf.cell(50, h, name, border=1, fill=fill)
            pdf.cell(60, h, email, border=1, fill=fill)
            pdf.cell(50, h, affil, border=1, fill=fill)
            pdf.set_text_color(*s_color)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(30, h, status, border=1, fill=fill, align="C")
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
            fill = not fill

    else:
        # ── Full report: Name | Email | Registered | Attended ────────────────
        cols = [("Name", 55), ("Email", 70), ("Registered", 35), ("Attended", 30)]
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(75, 46, 131)
        pdf.set_text_color(255, 255, 255)
        for col_name, width in cols:
            pdf.cell(width, 10, col_name, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        fill = False
        for p in participants:
            pdf.set_fill_color(245, 245, 245)
            name = str(p.get("name", "N/A"))[:30]
            email = str(p.get("email", "N/A"))[:38]
            registered = str(p.get("events_registered", 0))
            attended = str(p.get("events_attended", 0))

            pdf.set_text_color(0, 0, 0)
            pdf.cell(55, h, name, border=1, fill=fill)
            pdf.cell(70, h, email, border=1, fill=fill)
            pdf.cell(35, h, registered, border=1, fill=fill, align="C")
            a_color = (40, 167, 69) if int(attended) > 0 else (220, 53, 69)
            pdf.set_text_color(*a_color)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(30, h, attended, border=1, fill=fill, align="C")
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
            fill = not fill

    pdf_output = pdf.output(dest="S")
    return pdf_output
