from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArticleResponse(BaseModel):
    """기사 정보 응답 데이터."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    content_hash: str
    visibility: str
    title: str
    body: str
    media: str | None
    author: str | None
    category: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ArticleListResponse(BaseModel):
    """기사 목록 응답 데이터."""

    articles: list[ArticleResponse]
    total: int
