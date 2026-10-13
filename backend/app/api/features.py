from fastapi import APIRouter, Depends
from backend.services.features import (
    edit_service,
    recommend_service,
    review_service,
)
from backend.app.dependencies import get_current_user

router = APIRouter(prefix="/features", tags=["Features"])


@router.post("/conversations/{conversation_id}/review/full")
def request_full_review(
    conversation_id: int,
    user=Depends(get_current_user),
):
    pass


@router.post("/conversations/{conversation_id}/review/duplicate")
def request_duplicate_check(
    conversation_id: int,
    user=Depends(get_current_user),
):
    pass


@router.post("/conversations/{conversation_id}/review/fact")
def request_fact_check(
    conversation_id: int,
    user=Depends(get_current_user),
):
    pass


@router.post("/conversations/{conversation_id}/review/eval")
def request_article_evaluation(
    conversation_id: int,
    user=Depends(get_current_user),
):
    pass


@router.post("/conversations/{conversation_id}/recommend/title")
def request_title_recommendation(
    conversation_id: int,
    user=Depends(get_current_user),
):
    pass


@router.post("/conversations/{conversation_id}/recommend/keyword")
def request_keyword_recommendation(
    conversation_id: int,
    user=Depends(get_current_user),
):
    pass


@router.post("/conversations/{conversation_id}/recommend/ideas")
def request_article_ideas_recommendations(
    conversation_id: int,
    user=Depends(get_current_user),
):
    pass


@router.post("/conversations/{conversation_id}/format/{format_id}")
def request_article_formatting(
    conversation_id: int,
    format_id: int,
    user=Depends(get_current_user),
):
    pass