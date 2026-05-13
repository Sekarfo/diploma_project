from __future__ import annotations

from pydantic import BaseModel, Field


class SignUpRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=512)
    full_name: str = Field(min_length=1, max_length=255)


class SignInRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=512)


class AuthUser(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool


class AuthResponse(BaseModel):
    token_type: str
    access_token: str
    expires_at: str
    user: AuthUser


class AuthMeResponse(AuthUser):
    pass


class SignOutResponse(BaseModel):
    status: str
