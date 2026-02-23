from pydantic import BaseModel


class GitHubUser(BaseModel):
    id: int
    login: str
    name: str | None
    email: str | None
    avatar_url: str | None


class SessionUser(BaseModel):
    user_id: int
    name: str
    email: str | None
    avatar_url: str | None
