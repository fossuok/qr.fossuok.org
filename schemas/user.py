from pydantic import BaseModel, EmailStr


class CreateUser(BaseModel):
    name: str
    email: EmailStr


class VerifyUser(BaseModel):
    id: str
