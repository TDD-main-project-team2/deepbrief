from backend.repositories import article_repository
from backend.services.user import conversation_service
from backend.services.article import article_service
from backend.services.ai import model_service
from backend.schemas.message import MessageRequest
from sqlalchemy.orm import Session

# 템플릿 형식에 맞춰 기사 수정
def format_article_to_template(conversation_id, request: MessageRequest, current_user_id, db: Session):
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")
    article_template = article_repository.get_company_article_template()

    response = model_service.generate_formatted_article(article, article_template)
    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")
