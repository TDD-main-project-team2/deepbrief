from fastapi import APIRouter
from backend.services.auth import auth_service, password_service, token_service

router = APIRouter(prefix="/auth", tags=["Auth"])