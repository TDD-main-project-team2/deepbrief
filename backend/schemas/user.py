
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """회원가입 요청 데이터"""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    nickname: str = Field(min_length=1, max_length=255)
    organization_code: str = Field(min_length=1, max_length=50)
    admin_code: str = Field(min_length=1, max_length=50)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("닉네임을 입력해주세요.")
        return value


class UserResponse(BaseModel):
    """사용자 정보 응답 데이터"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nickname: str
    role: str