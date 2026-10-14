from fastapi import APIRouter, Depends, File, UploadFile, Form
from backend.services.user import conversation_service
from backend.app.dependencies import get_current_user
from backend.schemas.message import MessageRequest, MessageResponse
from backend.schemas.conversation import ConversationResponse



router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("/")
def get_conversations_by_user(current_user=Depends(get_current_user)):
    return conversation_service.get_conversations_by_user(current_user.id)

@router.post("/", response_model=ConversationResponse)
def create_conversation(
    file: UploadFile = File(...),
    title: str = Form(...),
    message: str = Form(...),
    current_user=Depends(get_current_user),
):
    initial_message = MessageRequest(role="user", content=message)
    return conversation_service.create_conversation(file, title, initial_message, current_user.id)

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