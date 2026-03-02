import os
from typing import Final

from fastapi import APIRouter, HTTPException, Cookie, Request, BackgroundTasks
from starlette.responses import RedirectResponse

from schemas import SessionUser
from services import (
    build_github_redirect_url,
    decode_session_cookie,
    handle_github_callback,
    log_auth_error,
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
    All business logic lives in services.auth.handle_github_callback.
    """
    code = request.query_params.get("code")

    if not code:
        error = request.query_params.get("error", "unknown")
        error_desc = request.query_params.get("error_description", "no code in callback")
        log_auth_error(error, error_desc, dict(request.query_params))
        return RedirectResponse(url="/?error=login_failed")

    http_client = request.app.state.http_client
    session_token, redirect_url = await handle_github_callback(
        code, http_client, background_tasks
    )

    if not session_token:
        raise HTTPException(status_code=401, detail="Supabase authentication failed")

    response = RedirectResponse(url=redirect_url)
    is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"

    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=MAX_AGE,
        expires=MAX_AGE,
    )
    return response


@router.get("/logout")
async def logout():
    """Clear the session cookie and redirect back to the homepage."""
    response = RedirectResponse(url="/")
    response.delete_cookie("session")
    return response
