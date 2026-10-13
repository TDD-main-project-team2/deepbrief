from fastapi import APIRouter, Depends
from backend.services.article import article_service
from backend.app.dependencies import get_current_user

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("/")
def get_articles_by_user(current_user=Depends(get_current_user)):
    # get article list by one user
    pass

@router.get("/{article_id}")
def get_article(article_id: int, current_user=Depends(get_current_user)):
    return article_service.get_article_by_id(article_id, current_user.id)

@router.post("/{article_id}", status_code=204)
def save_article(article_id: int, current_user=Depends(get_current_user)):
    article_service.save_article(article_id, current_user.id)

@router.delete("/{article_id}", status_code=204)
def delete_article(article_id: int, current_user=Depends(get_current_user)):
    article_service.delete_article(article_id, current_user.id)

@router.patch("/{article_id}/favorite")
def favorite_article_toggle(article_id: int, current_user=Depends(get_current_user)):
    return article_service.favorite_article_toggle(article_id, current_user.id)