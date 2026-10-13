from backend.repository import user_repository

# 사용자 정보 조회 (예시 코드)
def get_user(user_id):
    user = user_repository.find_user_by_id(user_id)
    return {
        user.username,
        user.password,
        user.email
    }

# 사용자 대화 목록 조회
def get_user_conversations():
    pass

# 사용자 특정 대화 조회
def get_user_conversation():
    pass