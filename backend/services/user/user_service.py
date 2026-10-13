from backend.repository import user_repository

# 사용자 정보 조회 (예시 코드)
def get_user_by_id(user_id):
    user = user_repository.find_user_by_id(user_id)
    return {
        user.username,
        user.password,
        user.email
    }