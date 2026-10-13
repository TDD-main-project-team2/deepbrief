from fastapi import APIRouter, Depends
from backend.services.auth import auth_service, password_service, token_service
from sqlalchemy.orm import Session
from backend.schemas.user import UserCreate, UserResponse
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.database.rdb.rdb import get_db


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    return auth_service.register_user(db, data)

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_user(db, data)

@router.post("/refresh")
def refresh():
    pass

@router.post("/logout")
def logout():
    pass