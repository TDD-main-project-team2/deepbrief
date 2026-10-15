from backend.services.document import article_processing_service
from backend.repositories import conversation_repository, message_repository
from backend.app.dependencies import ensure_owner, _not_found

# 사용자 대화 생성
async def create_conversation(file, title, current_user_id, rdb):
    file_bytes = await file.read()
    filename = file.filename
    article = article_processing_service.process_article(file_bytes, filename, rdb, reprocess=False)
    return conversation_repository.create_conversation(
        title,
        current_user_id,
        article.id
    )

def find_conversation_by_id(conversation_id):
    conversation = conversation_repository.find_conversation_by_id(conversation_id)
    if conversation is None:
        raise _not_found()
    return conversation

def find_message_by_id(message_id):
    message = message_repository.find_message_by_id(message_id)
    if message is None:
        raise _not_found()
    return message

# 사용자 대화 목록 조회
def get_conversations_by_user(current_user_id):
    return conversation_repository.find_all_by_user(current_user_id)

# 사용자 특정 대화 조회
def get_conversation_by_id(conversation_id, current_user_id):
    conversation = find_conversation_by_id(conversation_id)
    ensure_owner(conversation.user_id, current_user_id)
    return conversation

# 사용자 특정 대화 삭제
def delete_conversation(conversation_id, current_user_id):
    conversation = find_conversation_by_id(conversation_id)
    ensure_owner(conversation.user_id, current_user_id)
    conversation_repository.delete_conversation(conversation_id)

# 대화 기록 조회
def get_conversation_history(conversation_id, current_user_id, limit=5):
    conversation = find_conversation_by_id(conversation_id)
    ensure_owner(conversation.user_id, current_user_id)

    return message_repository.find_recent_by_conversation(
        conversation_id,
        limit=limit,
    )

def save_message(conversation_id, message: str, current_user_id, role:str):
    conversation = conversation_repository.find_conversation_by_id(conversation_id)
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
'''
def favorite_conversation_toggle(conversation_id, user_id):
    pass
'''