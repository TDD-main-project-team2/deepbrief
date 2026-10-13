from backend.schemas.message import MessageRequest


# 사용자 대화 목록 조회
def get_all_conversations(user_id):
    pass

# 사용자 특정 대화 조회
def get_conversation_by_id(conversation_id, user_id):
    pass

# 사용자 특정 대화 삭제
def delete_conversation_by_id(conversation_id, user_id):
    pass

def favorite_conversation_toggle(conversation_id, user_id):
    pass

def create_conversation(file, user_id):
    pass

def send_message(conversation_id, request: MessageRequest, user_id):
    request.content
    pass

def delete_message_by_id(message_id, user_id):
    pass