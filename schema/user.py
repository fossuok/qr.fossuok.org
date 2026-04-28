from typing import Literal, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, model_validator, Field


# ── Database Models ────────────────────────────────────────────────────────
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    qr_code_data: Optional[str] = None
    github_id: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    participant_type: Optional[str] = None   # 'uok_student' | 'other_university' | 'industry'
    student_id: Optional[str] = None         # UoK student ID
    university: Optional[str] = None         # Other university name
    study_year: Optional[str] = None         # e.g. "Year 2"
    organization: Optional[str] = None       # Industry org name
    job_role: Optional[str] = None           # Industry designation

    class Config:
        from_attributes = True


# ── Request Schemas ────────────────────────────────────────────────────────
class CreateUser(BaseModel):
    name: str
    email: EmailStr


class VerifyUser(BaseModel):
    id: str


class CompleteProfileRequest(BaseModel):
    """Submitted from the complete-profile form after first OAuth login."""
    participant_type: Literal["uok_student", "other_university", "industry"]

    # UoK students only
    student_id: Optional[str] = None

    # Other university students
    university: Optional[str] = None
    study_year: Optional[str] = None

    # Industry professionals
    organization: Optional[str] = None
    job_role: Optional[str] = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "CompleteProfileRequest":
        if self.participant_type == "uok_student":
            if not self.student_id or not self.student_id.strip():
                raise ValueError("Student ID is required for UoK students.")
        elif self.participant_type == "other_university":
            if not self.university or not self.university.strip():
                raise ValueError("University name is required.")
            if not self.study_year or not self.study_year.strip():
                raise ValueError("Year of study is required.")
        elif self.participant_type == "industry":
            if not self.organization or not self.organization.strip():
                raise ValueError("Organization name is required.")
            if not self.job_role or not self.job_role.strip():
                raise ValueError("Job role is required.")
        return self
