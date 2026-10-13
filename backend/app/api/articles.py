from fastapi import APIRouter
from backend.services.article import article_service

router = APIRouter(prefix="/articles", tags=["Articles"])



@router.get("/{article_id}")
def get_article(article_id: int):
    return article_service.get_article_by_id(article_id)

@router.post("/{article_id}", status_code=204)
def save_article(article_id: int):
    article_service.save_article(article_id)

@router.delete("/{article_id}", status_code=204)
def delete_article(article_id: int):
    article_service.delete_article(article_id)

@router.patch("/{article_id}/favorite")
def favorite_article_toggle(article_id: int):
    return article_service.favorite_article_toggle(article_id)