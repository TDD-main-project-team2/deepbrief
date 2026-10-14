from backend.services.article import article_service
from backend.services.user import conversation_service
from backend.services.ai import model_service
from backend.schemas.message import MessageRequest
from sqlalchemy.orm import Session


# 제목 및 부제목 추천
def recommend_title(conversation_id, request: MessageRequest, current_user_id, db: Session):
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_title(article)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

# 키워드/태그 추출
def recommend_keyword_tags(conversation_id, request: MessageRequest, current_user_id, db: Session):
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_keyword_tags(article)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

# 후속 기사 아이디어 추천
def recommend_article_ideas(conversation_id, request: MessageRequest, current_user_id, db: Session):
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_article_ideas(article)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")