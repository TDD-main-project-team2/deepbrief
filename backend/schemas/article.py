from pydantic import BaseModel

class ArticleResponse(BaseModel):
    title: str
    body: str

class ArticleListResponse(BaseModel):
    articles: list[ArticleResponse]
    total: int