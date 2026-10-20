from fastapi import APIRouter, Depends
from backend.services.features import (
    qa_service,
    edit_service,
    recommend_service,
    review_service,
)
from backend.services.resources import organization_service
from backend.schemas.message import MessageRequest, MessageResponse
from backend.app.dependencies import get_current_user
from backend.database.rdb.rdb import get_db
from sqlalchemy.orm import Session 


router = APIRouter(prefix="/features", tags=["Features"])

@router.post("/conversations/{conversation_id}/qa", response_model=MessageResponse)
async def ask_question(
    conversation_id: int,
    request: MessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await qa_service.ask_question(
        conversation_id, request, current_user.id, db
    )


@router.post("/conversations/{conversation_id}/review/duplicate", response_model=MessageResponse)
def request_duplicate_check(
    conversation_id: int,
    request: MessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return review_service.check_duplicates(conversation_id, request, current_user.id, db)


@router.post("/conversations/{conversation_id}/review/eval")
def request_article_evaluation(
    conversation_id: int,
    request: MessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return review_service.evaluate_article(conversation_id, request, current_user.id, db)


@router.post("/conversations/{conversation_id}/recommend/title")
def request_title_recommendation(
    conversation_id: int,
    request: MessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return recommend_service.recommend_title(conversation_id, request, current_user.id, db)


@router.post("/conversations/{conversation_id}/recommend/keyword")
def request_keyword_recommendation(
    conversation_id: int,
    request: MessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return recommend_service.recommend_keyword_tags(conversation_id, request, current_user.id, db)


@router.post("/conversations/{conversation_id}/recommend/headline", response_model=MessageResponse)
def request_headline_extraction(
    conversation_id: int,
    request: MessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return review_service.summarize_article(conversation_id, request, current_user.id, db)


@router.post("/conversations/{conversation_id}/recommend/ideas")
def request_article_ideas_recommendations(
    conversation_id: int,
    request: MessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return recommend_service.recommend_article_ideas(conversation_id, request, current_user.id, db)

@router.get("/templates")
def get_article_format_templates(
    current_user=Depends(get_current_user),
    db: Session=Depends(get_db)
):
    return organization_service.get_all_organization_article_templates(
        current_user.id,
        db,
    )

@router.post("/conversations/{conversation_id}/format/{template_id}")
def request_article_formatting(
    conversation_id: int,
    request: MessageRequest,
    template_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return edit_service.format_article_to_template(conversation_id, request, template_id, current_user.id, db)

'''
@router.post("/conversations/{conversation_id}/review/fact")
def request_fact_check(
    conversation_id: int,
    user=Depends(get_current_user),
):
    pass

'''
