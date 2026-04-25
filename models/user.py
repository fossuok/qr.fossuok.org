from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    qr_code_data: Optional[str] = None
    github_id: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Affiliation / profile fields collected after first login
    participant_type: Optional[str] = None   # 'uok_student' | 'other_university' | 'industry'
    student_id: Optional[str] = None         # UoK student ID
    university: Optional[str] = None         # Other university name
    study_year: Optional[str] = None         # e.g. "Year 2"
    organization: Optional[str] = None       # Industry org name
    job_role: Optional[str] = None           # Industry designation

    class Config:
        from_attributes: bool = True
