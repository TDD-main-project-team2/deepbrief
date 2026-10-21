from backend.services.document import article_processing_service
from backend.repositories import (article_repository, conversation_repository, message_repository)
from backend.app.dependencies import ensure_owner, _not_found
from backend.schemas.conversation import ConversationResponse


def _conversation_response(conversation, messages):
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        article_id=conversation.article_id,
        title=conversation.title,
        messages=messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )

async def create_conversation(file, title, article_visibility, current_user_id, rdb):
    file_bytes = await file.read()
    filename = file.filename
    mime_type = file.content_type

    article = article_processing_service.process_article(
        file_bytes,
        filename,
        mime_type,
        article_visibility,
        rdb,
        reprocess=False,
    )

    article_processing_service.categorize_article(article.id)

    article_repository.add_article_to_user(
        current_user_id,
        article.id,
    )

    conversation = conversation_repository.create_conversation(
        title,
        current_user_id,
        article.id,
    )
    
    messages = message_repository.find_messages_by_conversation_id(conversation.id)
    return _conversation_response(conversation, messages)

def find_conversation_by_id(conversation_id):
    conversation = conversation_repository.find_conversation_by_id(conversation_id)
    if conversation is None:
        raise _not_found()
    return conversation

def find_conversation_by_article_id(article_id: int):
    return conversation_repository.find_conversation_by_article_id(article_id)

def find_message_by_id(message_id):
    message = message_repository.find_message_by_id(message_id)
    if message is None:
        raise _not_found()
    return message

def get_conversations_by_user(current_user_id):
    return conversation_repository.find_all_by_user(current_user_id)

def get_conversation_by_id(conversation_id, current_user_id):
    conversation = find_conversation_by_id(conversation_id)
    ensure_owner(conversation.user_id, current_user_id)
    messages = message_repository.find_messages_by_conversation_id(conversation_id)
    return _conversation_response(conversation, messages)

def delete_conversation(conversation_id, current_user_id):
    conversation = find_conversation_by_id(conversation_id)
    ensure_owner(conversation.user_id, current_user_id)
    conversation_repository.delete_conversation(conversation_id)

def get_conversation_history(conversation_id, current_user_id, limit=5):
    conversation = find_conversation_by_id(conversation_id)
    ensure_owner(conversation.user_id, current_user_id)

    return message_repository.find_recent_by_conversation(
        conversation_id,
        limit=limit,
    )

def save_message(conversation_id, message: str, current_user_id, role:str):
    conversation = find_conversation_by_id(conversation_id)
    ensure_owner(conversation.user_id, current_user_id)
    return message_repository.create_message(
        conversation_id=conversation_id,
        content=message,
        role=role
    )

def delete_message(message_id, current_user_id):
    message = find_message_by_id(message_id)
    conversation = find_conversation_by_id(message.conversation_id)
    ensure_owner(conversation.user_id, current_user_id)
    message_repository.delete_message(message_id)
