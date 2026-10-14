from pydantic import BaseModel, EmailStr, Field

from backend.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """로그인 요청 데이터"""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    """로그인 성공 응답 데이터"""

    user: UserResponse
    access_token: str
    refresh_token: str
