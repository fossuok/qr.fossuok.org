import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks
from itsdangerous import URLSafeTimedSerializer

from config.supabase import supabase
from schemas import SessionUser
from .user import auto_register_user
from .mail import send_qr_email

load_dotenv()

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")
MAX_AGE = 86400  # 24 hours

_log = logging.getLogger("perf")


def build_github_redirect_url() -> str:
    """
    Uses the sync Supabase client to build OAuth URL for PKCE flow.
    This call is purely local (~2 ms) — no network round-trip — so running
    it synchronously is fine.  The sync client correctly stores the PKCE
    code verifier in-process for the later exchange_code_for_session call.
    """
    res = supabase.auth.sign_in_with_oauth({
        "provider": "github",
        "options": {
            "redirect_to": os.getenv("SUPABASE_GITHUB_CALLBACK_URL")
        }
    })
    return res.url


async def handle_supabase_callback(code: str):
    """Exchanges the PKCE code for a session and returns the user."""
    res = await asyncio.to_thread(
        supabase.auth.exchange_code_for_session, {"auth_code": code}
    )

    if not res or not res.user:
        return None

    return res.user


async def handle_github_callback(
    code: str,
    http_client,
    background_tasks: BackgroundTasks,
) -> tuple[str, str]:
    """
    Full OAuth callback pipeline — exchanges code, registers user,
    creates a session cookie, and queues the QR email.

    Returns (session_token, redirect_url).
    """
    supabase_user = await handle_supabase_callback(code)
    if not supabase_user:
        return None, None

    db_user = await auto_register_user(supabase_user)

    # Queue QR email in background for new registrations
    if "qr_data_url" in db_user:
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
        role=db_user.get("role", "participant"),
    )

    session_token = create_session_cookie(session_user.model_dump())
    redirect_url = "/admin/dashboard" if session_user.role == "admin" else "/user/registration-success"

    return session_token, redirect_url


def log_auth_error(error: str, error_desc: str, params: dict) -> None:
    """Log OAuth error details."""
    _log.info(
        "AUTH_ERR |          | %s: %s | params=%s",
        error, error_desc, params,
    )


def create_session_cookie(user_data: dict) -> str:
    serializer = URLSafeTimedSerializer(APP_SECRET_KEY)
    return serializer.dumps(user_data)


def decode_session_cookie(token: str) -> Optional[SessionUser]:
    serializer = URLSafeTimedSerializer(APP_SECRET_KEY)
    try:
        session_data = serializer.loads(token, max_age=MAX_AGE)
        return SessionUser(**session_data)
    except Exception:
        return None
