from backend.services.user import conversation_service
from backend.services.ai import model_service
from backend.schemas.message import MessageRequest

# 제목 및 부제목 추천
def recommend_title(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_title(request.content)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

# 키워드/태그 추출
def recommend_keyword_tags(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_keyword_tags(request.content)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

# 후속 기사 아이디어 추천
def recommend_article_ideas(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_article_ideas(request.content)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")