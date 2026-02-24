from .auth import (
    build_github_redirect_url,
    handle_supabase_callback,
    create_session_cookie,
    decode_session_cookie
)
from .user import auto_register_user, verify_user, get_qr_image
from .mail import send_qr_email
from .event import get_active_event, get_event_by_id

__all__ = [
    "register_user",
    "verify_user",
    "get_qr_image",
    "send_qr_email",
    "build_github_redirect_url",
    "handle_supabase_callback",
    "create_session_cookie",
    "decode_session_cookie",
    "get_active_event",
    "get_event_by_id"
]
