from os import getenv

import httpx
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.orm import Session

from models import User
from schemas import GitHubUser, SessionUser

load_dotenv()

APP_SECRET_KEY = getenv("APP_SECRET_KEY")
GITHUB_CLIENT_ID = getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = getenv("GITHUB_CLIENT_SECRET")


def build_github_redirect_url() -> str:
    """Build the GitHub OAuth redirect URL."""
    return f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=user:email"


def exchange_code_for_token(code: str) -> str:
    url: str = "https://github.com/login/oauth/access_token"
    headers: dict[str, str] = {"Accept": "application/json"}
    params: dict[str, str] = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code
    }

    response: httpx.Response = httpx.post(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return data["access_token"]


def fetch_github_user(access_token: str) -> GitHubUser:
    """Fetch the GitHub user from the GitHub API."""
    url: str = "https://api.github.com/user"
    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}

    response: httpx.Response = httpx.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return GitHubUser(**data)


def get_or_create_user(github_user: GitHubUser, access_token: str, db: Session) -> User:
    """Get or create a user from the GitHub user."""
    user: User | None = db.query(User).filter(User.github_id == str(github_user.id)).first()
    if user:
        return user

    user: User = User(
        github_id=str(github_user.id),
        access_token=access_token,
        name=github_user.name,
        email=github_user.email,
        avatar_url=github_user.avatar_url
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session_cookie(user: User) -> str:
    serializer = URLSafeTimedSerializer(APP_SECRET_KEY)
    session_data = {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url
    }
    return serializer.dumps(session_data)


def decode_session_cookie(token: str) -> SessionUser | None:
    serializer = URLSafeTimedSerializer(APP_SECRET_KEY)
    try:
        session_data = serializer.loads(token, max_age=86_400)
        return SessionUser(**session_data)
    except Exception:
        return None
