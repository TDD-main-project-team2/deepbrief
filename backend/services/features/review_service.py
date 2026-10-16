from backend.services.resources import article_service, conversation_service, organization_service
from backend.services.ai import model_service
from backend.schemas.message import MessageRequest
from sqlalchemy.orm import Session
from backend.services.rag import rag_service


def check_duplicates(conversation_id, request: MessageRequest, current_user_id, db: Session):
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    article_chunks = rag_service.retrieve_article_chunks(article.id)
    similar_chunks = {}
    for chunk in article_chunks:
        matches = rag_service.retrieve_org_chunks_by_embedding(chunk.embedding, article.id)
        for match in matches:
            similar_chunks[match.id] = match

    similar_chunks = list(similar_chunks.values())
        
    article_context = rag_service.build_context(article_chunks)
    similar_context = rag_service.build_context(similar_chunks)
    response = model_service.generate_duplicate_check(article_context, similar_context)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

def evaluate_article(conversation_id, request: MessageRequest, current_user_id, db: Session):
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")
    eval_guideline = organization_service.get_organization_evaluation_guideline_for_user(current_user_id, 1)

    response = model_service.generate_article_evaluation(article, eval_guideline)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

def summarize_article(conversation_id, request: MessageRequest, current_user_id, db: Session):
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_summary(article)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")

'''
# Option
def fact_check(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = model_service.generate_summary(request.content)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")
'''