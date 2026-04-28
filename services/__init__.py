from .auth import (
    build_github_redirect_url,
    handle_supabase_callback,
    handle_github_callback,
    log_auth_error,
    create_session_cookie,
    decode_session_cookie,
)
from .user import (
    auto_register_user, verify_user, get_qr_image, generate_qr_data_url,
    get_user_profile, complete_user_profile,
)
from .mail import send_qr_email
from .event import get_active_event, get_event_by_id
from .registration import (
    get_user_registrations,
    get_all_active_events,
    register_for_event,
    verify_registration,
    get_registration_qr_payload,
)

__all__ = [
    "auto_register_user",
    "verify_user",
    "get_qr_image",
    "generate_qr_data_url",
    "get_user_profile",
    "complete_user_profile",
    "send_qr_email",
    "build_github_redirect_url",
    "handle_supabase_callback",
    "handle_github_callback",
    "log_auth_error",
    "create_session_cookie",
    "decode_session_cookie",
    "get_active_event",
    "get_event_by_id",
    "get_user_registrations",
    "get_all_active_events",
    "register_for_event",
    "verify_registration",
    "get_registration_qr_payload",
]

