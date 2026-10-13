from backend.repositories import user_repository


# 필요 없나???
# 사용자 정보 조회 (예시 코드)
def get_user_by_id(user_id):
    return user_repository.find_user_by_id(user_id)