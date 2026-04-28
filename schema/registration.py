from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Registration(BaseModel):
    id: Optional[str] = None
    user_qr_code: str
    event_id: str
    registered_at: Optional[datetime] = None
    attended_at: Optional[datetime] = None

    class Config:
        from_attributes = True
