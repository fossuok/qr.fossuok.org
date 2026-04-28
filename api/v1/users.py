import asyncio
import base64
import io

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from api.v1.auth import get_current_user
from schema.user import CompleteProfileRequest
from services import get_qr_image
from services.mail import send_qr_email
from services.registration import (
    get_user_registrations,
    get_all_active_events,
    register_for_event as _register_for_event,
    get_registration_qr_payload,
    _generate_qr_data_url,
)
from services.user import get_user_profile, complete_user_profile

router: APIRouter = APIRouter(
    prefix="/user",
    tags=["User"]
)

templates: Jinja2Templates = Jinja2Templates(directory="templates")

STUDY_YEARS: list[str] = ["Year 1", "Year 2", "Year 3", "Year 4", "Postgraduate"]


# Profile completion

@router.get("/complete-profile", response_class=HTMLResponse)
async def complete_profile_page(request: Request, user=Depends(get_current_user)):
    """Show affiliation form for new users. Skip if already complete."""
    profile = await get_user_profile(user.user_id)
    if profile and profile.get("participant_type"):
        return RedirectResponse(url="/user/events", status_code=302)

    return templates.TemplateResponse("complete_profile.html", {
        "request": request,
        "user": user,
        "study_years": STUDY_YEARS,
    })


@router.post("/complete-profile")
async def submit_complete_profile(
        request: Request,
        user=Depends(get_current_user),
        participant_type: str = Form(...),
        student_id: str = Form(default=""),
        university: str = Form(default=""),
        study_year: str = Form(default=""),
        organization: str = Form(default=""),
        job_role: str = Form(default=""),
):
    """Save affiliation and redirect to event selection."""
    try:
        profile = CompleteProfileRequest(
            participant_type=participant_type,
            student_id=student_id or None,
            university=university or None,
            study_year=study_year or None,
            organization=organization or None,
            job_role=job_role or None,
        )
    except ValidationError as exc:
        error_msg = exc.errors()[0]["msg"] if exc.errors() else "Invalid input."
        return templates.TemplateResponse("complete_profile.html", {
            "request": request,
            "user": user,
            "study_years": STUDY_YEARS,
            "error": error_msg,
            "form": {
                "participant_type": participant_type,
                "student_id": student_id,
                "university": university,
                "study_year": study_year,
                "organization": organization,
                "job_role": job_role,
            },
        }, status_code=422)

    await complete_user_profile(user.user_id, profile.model_dump())
    return RedirectResponse(url="/user/events", status_code=302)


# Event selection & registration
@router.get("/events", response_class=HTMLResponse)
async def user_events_page(request: Request, user=Depends(get_current_user)):
    """
    Main participant landing page.
    Shows events the user is already registered for and any open event they can join.
    """
    profile = await get_user_profile(user.user_id)
    if not profile or not profile.get("participant_type"):
        return RedirectResponse(url="/user/complete-profile", status_code=302)

    registrations, active_events = await asyncio.gather(
        get_user_registrations(user.user_id),
        get_all_active_events(),
    )

    # Merge event details into registrations in the router
    events_by_id = {str(e["id"]): e for e in active_events}
    for reg in registrations:
        reg["event"] = events_by_id.get(str(reg["event_id"]), {})

    registered_ids = {str(r["event_id"]) for r in registrations}
    available = [e for e in active_events if str(e["id"]) not in registered_ids]

    return templates.TemplateResponse("user_events.html", {
        "request": request,
        "user": user,
        "registrations": registrations,
        "available_events": available,
    })


@router.post("/events/{event_id}/register")
async def register_for_event(
        event_id: str,
        request: Request,
        background_tasks: BackgroundTasks,
        user=Depends(get_current_user),
):
    """Register the current user for an event, generate per-event QR, queue email."""
    result = await _register_for_event(user.user_id, event_id, user.name, user.email)

    background_tasks.add_task(
        send_qr_email,
        user.email,
        user.name,
        result["qr_data_url"],
        request.app.state.http_client,
    )

    return RedirectResponse(url="/user/events?registered=1", status_code=302)


# ── Per-registration QR download ────────────────────────────────────────────

@router.get("/registrations/{registration_id}/qr")
async def download_registration_qr(
        registration_id: str,
        user=Depends(get_current_user),
):
    """Stream the QR PNG for a specific event registration (user must own it)."""
    payload = await get_registration_qr_payload(registration_id, user.user_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Registration not found.")

    qr_data_url = await asyncio.to_thread(_generate_qr_data_url, payload)
    # Strip the data URL prefix and decode
    b64 = qr_data_url.split(",", 1)[1]
    buf = io.BytesIO(base64.b64decode(b64))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={registration_id}.png"},
    )


# Legacy routes

@router.get("/registration-success", response_class=HTMLResponse)
async def registration_success(request: Request, user=Depends(get_current_user)):
    """Kept for backward compatibility — redirects to the new events page."""
    return RedirectResponse(url="/user/events", status_code=302)


@router.get("/events/{qr_data}/qr")
async def download_qr(qr_data: str):
    """Stream a legacy user-level QR code PNG."""
    try:
        return get_qr_image(qr_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
