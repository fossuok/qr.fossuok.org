import os
from typing import Final

from fastapi import APIRouter, HTTPException, Cookie, Request, BackgroundTasks
from starlette.responses import RedirectResponse

from schemas import SessionUser
from services import (
    build_github_redirect_url,
    handle_supabase_callback,
    create_session_cookie,
    decode_session_cookie
)

router: APIRouter = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

MAX_AGE: Final[int] = 86400


async def get_current_user(session: str | None = Cookie(default=None)):
    """Dependency - reads the signed session cookie and returns the SessionUser."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_user: SessionUser | None = decode_session_cookie(session)
    if not session_user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session_user


@router.get("/github")
async def github_login():
    """Redirect to Supabase Auth."""
    return RedirectResponse(url=build_github_redirect_url())


@router.get("/callback")
async def github_callback(request: Request, background_tasks: BackgroundTasks):
    """
    Handle the callback from Supabase (PKCE flow).
    """
    code = request.query_params.get("code")
    
    if not code:
        # Supabase may send error details when OAuth fails (stale session, etc.)
        error = request.query_params.get("error", "unknown")
        error_desc = request.query_params.get("error_description", "no code in callback")
        
        import logging
        logging.getLogger("perf").info(
            "AUTH_ERR |          | %s: %s | params=%s",
            error, error_desc, dict(request.query_params),
        )
        
        # Redirect back to login so the user can retry immediately
        return RedirectResponse(url="/?error=login_failed")

    supabase_user = await handle_supabase_callback(code)
    if not supabase_user:
        raise HTTPException(status_code=401, detail="Supabase authentication failed")

    # AUTO-REGISTRATION: Sync user data and link to active event
    from services import auto_register_user, send_qr_email
    db_user = await auto_register_user(supabase_user)
    
    # Send QR email in background if it's a new registration or needs resending.
    # Pass the app-level shared httpx client to avoid a new TCP connection per email.
    if "qr_data_url" in db_user:
        http_client = request.app.state.http_client
        background_tasks.add_task(
            send_qr_email,
            db_user["email"],
            db_user["name"],
            db_user["qr_data_url"],
            http_client,
        )

    session_user = SessionUser(
        user_id=db_user["qr_code_data"],
        name=db_user["name"],
        email=db_user["email"],
        avatar_url=db_user.get("avatar_url"),
        role=db_user.get("role", "participant")
    )
    
    session_token: str = create_session_cookie(session_user.model_dump())

    # ROLE-BASED REDIRECTION
    redirect_url = "/admin/dashboard" if session_user.role == "admin" else "/user/registration-success"
    response = RedirectResponse(url=redirect_url)
    
    # 86400 seconds = 24 hours
    MAX_AGE = 86400
    is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"

    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=MAX_AGE,
        expires=MAX_AGE
    )
    return response


@router.get("/logout")
async def logout():
    """Clear the session cookie and redirect back to the homepage."""
    response = RedirectResponse(url="/")
    response.delete_cookie("session")
    return response
