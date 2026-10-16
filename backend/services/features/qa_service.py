from backend.services.resources import conversation_service, article_service
from backend.services.agent import graph
from backend.schemas.message import MessageRequest

async def ask_question(conversation_id, question: MessageRequest, current_user_id, db):
    conversation_service.save_message(conversation_id, question.content, current_user_id, "user")

    conversation_history = conversation_service.get_conversation_history(conversation_id, current_user_id)
    article = article_service.get_article_by_conversation_id(conversation_id, current_user_id, db)

    result = await graph.run_agent(question.content, article.id, conversation_history)
    response = result["answer"]

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")