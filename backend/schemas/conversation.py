from pydantic import BaseModel
from .message import MessageResponse

class ConversationResponse(BaseModel):
    title: str
    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int