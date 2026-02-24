from pydantic import BaseModel


class GitHubUser(BaseModel):
    id: int
    login: str
    name: str | None
    email: str | None
    avatar_url: str | None


class SessionUser(BaseModel):
    user_id: str
    name: str
    email: str | None
    avatar_url: str | None
    role: str = "participant"
