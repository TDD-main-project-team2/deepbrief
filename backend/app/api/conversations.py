from fastapi import APIRouter, Depends, File, UploadFile, Form
from backend.services.resources import conversation_service
from backend.app.dependencies import get_current_user
from backend.schemas.conversation import ConversationResponse
from sqlalchemy.orm import Session
from backend.database.rdb.rdb import get_db



router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("/")
def get_conversations_by_user(current_user=Depends(get_current_user)):
    return conversation_service.get_conversations_by_user(current_user.id)

@router.post("/", response_model=ConversationResponse)
def create_conversation(
    file: UploadFile = File(...),
    title: str = Form(...),
    article_visibility: str=Form(...),
    current_user=Depends(get_current_user),
    rdb: Session = Depends(get_db)
):
    return conversation_service.create_conversation(file, title, article_visibility, current_user.id, rdb)

@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    current_user=Depends(get_current_user),
):
    return conversation_service.get_conversation_by_id(
        conversation_id, current_user.id
    )

@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    current_user=Depends(get_current_user),
):
    conversation_service.delete_conversation(conversation_id, current_user.id)

@router.delete("/message/{message_id}", status_code=204)
def delete_message(
    message_id: int,
    current_user=Depends(get_current_user),
):
    conversation_service.delete_message(message_id, current_user.id)

'''
@router.patch("/{conversation_id}/favorite")
def favorite_conversation_toggle(
    conversation_id: int,
    current_user=Depends(get_current_user),
):
    return conversation_service.favorite_conversation_toggle(
        conversation_id, current_user.id
    )
'''