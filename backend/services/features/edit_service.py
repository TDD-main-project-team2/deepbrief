from backend.services.resources import conversation_service, article_service, organization_service
from backend.services.ai import model_service
from backend.schemas.message import MessageRequest
from sqlalchemy.orm import Session

# 템플릿 형식에 맞춰 기사 수정
def format_article_to_template(conversation_id, request: MessageRequest, template_id: int, current_user_id, db: Session):
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")
    article_template = organization_service.get_organization_article_template_for_user(current_user_id,  template_id)

    response = model_service.generate_formatted_article(article, article_template)
    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")
