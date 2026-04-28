import asyncio
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.datastructures import FormData

from api.v1.auth import get_current_user
from services.admin import (
    fetch_user_stat, generate_pdf, get_paginated_users, get_all_participants,
    get_participants_for_event, change_user_role, delete_user_from_db,
    invalidate_users_cache, invalidate_stat_cache
)
from services.event import get_active_event
from services.event import (
    get_all_events, add_event, toggle_event_status,
    delete_event_data, update_event_data
)
from services.registration import invalidate_active_events_cache

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
    (total_registered, total_attended), active_event = await asyncio.gather(
        fetch_user_stat(),
        get_active_event()
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "active_event": active_event,
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
async def export_attendance(user=Depends(get_current_user)):
    """Full attendance PDF — all participants across all events."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    participants = await get_all_participants()
    pdf_output = generate_pdf(participants, event_title="All Events", per_event=False)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return StreamingResponse(
        io.BytesIO(pdf_output),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=attendance_all_{ts}.pdf"}
    )


@router.get("/export-attendance/{event_id}")
async def export_attendance_event(event_id: str, user=Depends(get_current_user)):
    """Per-event attendance PDF."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    participants, event = await get_participants_for_event(event_id)
    event_title = event.get("title", "Event") if event else "Event"
    pdf_output = generate_pdf(participants, event_title=event_title, per_event=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_title = event_title.replace(" ", "_")[:30]
    return StreamingResponse(
        io.BytesIO(pdf_output),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=attendance_{safe_title}_{ts}.pdf"}
    )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
        request: Request,
        page: int = 1,
        limit: int = 15,
        search: str = "",
        user=Depends(get_current_user)
):
    """Admin page — lists registered users with server-side pagination."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    page = max(1, page)
    result = await get_paginated_users(page=page, limit=limit, search=search)

    total_pages = result["pages"]
    if page > total_pages and total_pages > 0:
        return RedirectResponse(url=f"/admin/users?page={total_pages}&search={search}", status_code=302)

    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "user": user,
        "users_list": result["users"],
        "page": result["page"],
        "limit": limit,
        "search": search,
        "total_count": result["total"],
        "total_pages": result["pages"],
    })


@router.post("/users/{github_id}/promote")
async def promote_user(
        github_id: str,
        user=Depends(get_current_user)
):
    """Promote a user to admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    err, status = await change_user_role(github_id, "admin")
    if not status:
        raise HTTPException(status_code=500, detail=f"Failed to promote user: {str(err)}")
    invalidate_users_cache()
    invalidate_stat_cache()
    return RedirectResponse(url="/admin/users?success=promoted", status_code=303)


@router.post("/users/{github_id}/demote")
async def demote_user(
        github_id: str,
        user=Depends(get_current_user)
):
    """Demote an admin back to participant role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    err, status = await change_user_role(github_id, "participant")
    if not status:
        raise HTTPException(status_code=500, detail=f"Failed to demote user: {str(err)}")
    invalidate_users_cache()
    invalidate_stat_cache()
    return RedirectResponse(url="/admin/users?success=demoted", status_code=303)


@router.post("/users/{github_id}/delete")
async def delete_user(
        github_id: str,
        user=Depends(get_current_user)
):
    """Delete a user from the system."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    err, status = await delete_user_from_db(github_id)
    if not status:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(err)}")
    invalidate_users_cache()
    invalidate_stat_cache()
    return RedirectResponse(url="/admin/users?success=deleted", status_code=303)


@router.get("/events", response_class=HTMLResponse)
async def admin_events(
        request: Request,
        user=Depends(get_current_user)
):
    """Admin page — lists all events."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    events_list = await get_all_events()

    return templates.TemplateResponse("admin_events.html", {
        "request": request,
        "user": user,
        "events_list": events_list,
    })


@router.post("/events/create")
async def create_event(
        request: Request,
        user=Depends(get_current_user)
):
    """Create a new event from form data."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    form: FormData = await request.form()

    err, status, code = await add_event(form)
    if not status:
        raise HTTPException(status_code=code, detail=err)
    invalidate_active_events_cache()
    return RedirectResponse(url="/admin/events?success=created", status_code=303)


@router.post("/events/{event_id}/edit")
async def edit_event(
        event_id: str,
        request: Request,
        user=Depends(get_current_user)
):
    """Update an existing event from form data."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    form = await request.form()

    err, status, code = await update_event_data(form, event_id)
    if not status:
        raise HTTPException(status_code=code, detail=err)
    invalidate_active_events_cache()
    return RedirectResponse(url="/admin/events?success=updated", status_code=303)


@router.post("/events/{event_id}/toggle")
async def toggle_event(
        event_id: str,
        user=Depends(get_current_user)
):
    """Toggle an event's active status. Deactivates all others when activating."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    status, is_success = await toggle_event_status(event_id)
    if not is_success:
        raise HTTPException(status_code=500, detail=f"Failed to toggle event: {str(status)}")
    invalidate_active_events_cache()
    return RedirectResponse(url=f"/admin/events?success={status}", status_code=303)


@router.post("/events/{event_id}/delete")
async def delete_event(
        event_id: str,
        user=Depends(get_current_user)
):
    """Delete an event."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    err, is_success = await delete_event_data(event_id)
    if not is_success:
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {str(err)}")
    invalidate_active_events_cache()
    return RedirectResponse(url="/admin/events?success=event_deleted", status_code=303)
