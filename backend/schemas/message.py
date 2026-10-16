from pydantic import BaseModel

class MessageRequest(BaseModel):
    id: int
    role: str
    content: str

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str