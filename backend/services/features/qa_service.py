from backend.services.user import conversation_service
from backend.services.ai import model_service
from backend.schemas.message import MessageRequest, MessageResponse

# 질문 답변
def ask_question(conversation_id, request: MessageRequest, current_user_id):
    conversation_service.save_message(conversation_id, request.content, current_user_id, "user")

    response = answer_question(request)

    return conversation_service.save_message(conversation_id, response, current_user_id, "assistant")


def answer_question(request: MessageRequest):
    return model_service.answer_qa(request.content)