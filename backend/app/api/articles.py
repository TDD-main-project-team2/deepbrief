from fastapi import APIRouter, Depends
from backend.services.article import article_service
from backend.app.dependencies import get_current_user
from backend.schemas.article import ArticleResponse, ArticleListResponse


router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("/", response_model=ArticleListResponse)
def get_articles_by_user(current_user=Depends(get_current_user)):
    return article_service.get_articles_by_user(current_user.id)

@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, current_user=Depends(get_current_user)):
    return article_service.get_article_by_id(article_id, current_user.id)

@router.post("/{article_id}", status_code=204)
def save_article(article_id: int, current_user=Depends(get_current_user)):
    article_service.save_article(article_id, current_user.id)

@router.delete("/{article_id}", status_code=204)
def delete_article(article_id: int, current_user=Depends(get_current_user)):
    article_service.delete_article(article_id, current_user)

# Option
@router.patch("/{article_id}/favorite", response_model=ArticleResponse)
def favorite_article_toggle(article_id: int, current_user=Depends(get_current_user)):
    return article_service.favorite_article_toggle(article_id, current_user.id)

# ArticleResponse, ArticleListResponse 추가 필요 (no request)