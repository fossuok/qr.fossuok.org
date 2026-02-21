from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from config import Base


class User(Base):
    __tablename__ = "users"

    id: Column[int] = Column(Integer, primary_key=True, index=True)
    name: Column[str] = Column(String, nullable=False)
    email: Column[str] = Column(String, unique=True, nullable=False)
    qr_code_data: Column[str] = Column(String, nullable=False, unique=True)

    created_at: Column[datetime] = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Column[datetime] = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name}, email={self.email})"
