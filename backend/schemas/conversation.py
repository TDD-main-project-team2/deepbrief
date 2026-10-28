from datetime import datetime

from pydantic import BaseModel, ConfigDict
from .message import MessageResponse


class ConversationResponse(BaseModel):
    """대화 정보 응답 스키마."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    article_id: int
    title: str
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime

class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
