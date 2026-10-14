from backend.repositories import article_repository
from backend.services.user import conversation_service
from backend.services.ai import model_service
from backend.schemas.message import MessageRequest

# 중복 기사 탐지
# 미완료!!!!!!!
def check_duplicates(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    # Vector DB 로직 필요

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

# 회사 지침 기반 기사 평가
def evaluate_article(conversation_id, request: MessageRequest, current_user_id):
    article = article_repository.find_article_by_conversation_id(conversation_id)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")
    eval_guideline = article_repository.get_company_evaluation_guideline()

    response = model_service.generate_article_evaluation(article, eval_guideline)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

def summarize_article(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_summary(request.content)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

'''
# Option
def fact_check(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_summary(request.content)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")
'''