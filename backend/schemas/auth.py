from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    """로그인 요청 데이터"""
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)