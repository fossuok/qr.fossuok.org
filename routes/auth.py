from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Cookie
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from config import get_db
from services import (
    build_github_redirect_url,
    get_or_create_user,
    create_session_cookie,
    exchange_code_for_token,
    fetch_github_user,
    decode_session_cookie
)

router: APIRouter = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

db_dep = Annotated[Session, Depends(get_db)]


# ── Reusable dependency ────────────────────────────────────────────────────────

async def get_current_user(session: str | None = Cookie(default=None)):
    """Dependency — reads the signed session cookie and returns the SessionUser."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_user = decode_session_cookie(session)
    if not session_user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session_user


# ── OAuth routes ───────────────────────────────────────────────────────────────

@router.get("/github")
async def github_login():
    """Redirect the admin to GitHub's OAuth authorization page."""
    return RedirectResponse(url=build_github_redirect_url())


@router.get("/github/callback")
async def github_callback(code: str, db: db_dep):
    """Handle the GitHub OAuth callback, create/update the user, set session cookie."""
    access_token: str = exchange_code_for_token(code)
    github_user = fetch_github_user(access_token)
    user = get_or_create_user(github_user, access_token, db)
    session_token: str = create_session_cookie(user)

    response = RedirectResponse(url="/admin/dashboard")
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        samesite="lax"
    )
    return response


@router.get("/logout")
async def logout():
    """Clear the session cookie and redirect back to the homepage."""
    response = RedirectResponse(url="/")
    response.delete_cookie("session")
    return response
