from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRequest(BaseModel):
    """메시지 생성 요청 스키마."""

    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("메시지를 입력해주세요.")
        return value


class MessageResponse(BaseModel):
    """메시지 응답 스키마."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    updated_at: datetime