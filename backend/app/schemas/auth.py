"""Authentication schemas."""
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Access token response."""
    access_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Refresh token response."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User data response."""
    id: int
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
