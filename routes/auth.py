import os
from typing import Final

from fastapi import APIRouter, HTTPException, Cookie, Request
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
    """Dependency — reads the signed session cookie and returns the SessionUser."""
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
async def github_callback(request: Request):
    """
    Handle the callback from Supabase (PKCE flow).
    """
    code = request.query_params.get("code")

    if not code:
        # If no code in query, it's either an error or still using implicit flow
        return {
            "message": "Auth code not found. Please ensure PKCE is enabled in Supabase or check your redirect settings."}

    supabase_user = await handle_supabase_callback(code)
    if not supabase_user:
        raise HTTPException(status_code=401, detail="Supabase authentication failed")

    session_user = SessionUser(
        user_id=supabase_user.id,
        name=supabase_user.user_metadata.get("full_name") or supabase_user.email,
        email=supabase_user.email,
        avatar_url=supabase_user.user_metadata.get("avatar_url")
    )

    session_token: str = create_session_cookie(session_user.model_dump())

    response = RedirectResponse(url="/admin/dashboard")

    # Enable secure=True in production (requires HTTPS)
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
