import io
from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.datastructures import FormData

from routes.auth import get_current_user
from services.admin import fetch_user_stat, generate_pdf, get_all_users, get_all_participants, change_user_role, \
    delete_user_from_db
from services.event import get_all_events, add_event, toggle_event_status, delete_event_data, update_event_data

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
    total_registered, total_attended = await fetch_user_stat()

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
    """Admin page — lists all registered users with their roles."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # get the users from supabase
    users = await get_all_participants()

    # Output as stream
    pdf_output = generate_pdf(users)

    return StreamingResponse(
        io.BytesIO(pdf_output),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
    )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
        request: Request,
        user=Depends(get_current_user)
):
    """Admin page — lists all registered users with their roles."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    users_list = await get_all_users()

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

    err, status = await change_user_role(github_id, "admin")
    if not status:
        raise HTTPException(status_code=500, detail=f"Failed to promote user: {str(err)}")
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
    return RedirectResponse(url="/admin/events?success=event_deleted", status_code=303)
