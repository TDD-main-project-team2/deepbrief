from pydantic import BaseModel, Field


class OrgTemplateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)

class OrgGuidelineRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)

class OrgTemplateResponse(BaseModel):
    id: int
    title: str
    content: str

class OrgGuidelineResponse(BaseModel):
    id: int
    title: str
    content: str