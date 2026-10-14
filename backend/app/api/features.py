from fastapi import APIRouter, Depends
from backend.services.features import (
    qa_service,
    edit_service,
    recommend_service,
    review_service,
)
from backend.schemas.message import MessageRequest, MessageResponse
from backend.app.dependencies import get_current_user

router = APIRouter(prefix="/features", tags=["Features"])

@router.post("/conversations/{conversation_id}/qa", response_model=MessageResponse)
def ask_question(
    conversation_id: int,
    request: MessageRequest,
    current_user=Depends(get_current_user),
):
    return qa_service.ask_question(
        conversation_id, request, current_user.id
    )

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