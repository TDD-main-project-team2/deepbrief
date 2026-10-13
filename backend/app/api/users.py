from fastapi import APIRouter
from backend.services.user import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/user/{id}")
def get_user(user_id):
    return user_service.get_user(user_id)