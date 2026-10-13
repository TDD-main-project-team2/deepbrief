from fastapi import APIRouter, Depends, File, UploadFile
from backend.services.features import qa_service, edit_service, recommend_service, review_service
from backend.services.user import conversation_service
from backend.app.dependencies import get_current_user
from backend.schemas.message import MessageRequest


router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("/")
def get_all_conversations(user=Depends(get_current_user)):
    return conversation_service.get_user_conversations(user.id)


@router.post("/")
def create_conversation(file: UploadFile = File(...), user=Depends(get_current_user)):
    return conversation_service.create_conversation(file, user.id)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int, user=Depends(get_current_user)):
    return conversation_service.get_conversation_by_id(conversation_id, user.id)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, user=Depends(get_current_user)):
    conversation_service.delete_conversation_by_id(conversation_id, user.id)


@router.patch("/{conversation_id}/favorite")
def favorite_conversation_toggle(conversation_id: int, user=Depends(get_current_user)):
    conversation_service.favorite_conversation_toggle(conversation_id, user.id)


@router.post("/message")
def send_message(conversation_id: int, request: MessageRequest, user=Depends(get_current_user)):
    return conversation_service.send_message(conversation_id, request, user.id)


@router.delete("/message/{message_id}", status_code=204)
def delete_message(message_id: int, user=Depends(get_current_user)):
    conversation_service.delete_message_by_id(message_id, user.id)