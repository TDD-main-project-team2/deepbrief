from backend.services.user import conversation_service
from backend.services.ai import model_service
from backend.schemas.message import MessageRequest

# 질문 답변
# rag 추가 필요
def ask_question(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    # agent logic add
    response = model_service.generate_answer(request.content)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")