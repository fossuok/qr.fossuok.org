import asyncio
import os
from typing import Optional

from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer

from config.supabase import supabase
from schemas import SessionUser

load_dotenv()

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")


def build_github_redirect_url() -> str:
    """Uses Supabase client to build OAuth URL for PKCE flow."""
    res = supabase.auth.sign_in_with_oauth({
        "provider": "github",
        "options": {
            "redirect_to": os.getenv('SUPABASE_GITHUB_CALLBACK_URL')
        }
    })
    return res.url


async def handle_supabase_callback(code: str):
    """Exchanges the PKCE code for a session and returns the user."""
    res = await asyncio.to_thread(supabase.auth.exchange_code_for_session, {"auth_code": code})
    return res.user


def create_session_cookie(user_data: dict) -> str:
    serializer = URLSafeTimedSerializer(APP_SECRET_KEY)
    return serializer.dumps(user_data)


def decode_session_cookie(token: str) -> Optional[SessionUser]:
    serializer = URLSafeTimedSerializer(APP_SECRET_KEY)
    try:
        session_data = serializer.loads(token, max_age=86_400)
        return SessionUser(**session_data)
    except Exception:
        return None
