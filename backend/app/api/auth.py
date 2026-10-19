from fastapi import APIRouter, Depends
from backend.services.auth import auth_service, token_service
from sqlalchemy.orm import Session
from backend.schemas.user import UserCreate, UserResponse
from backend.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse, LogoutRequest
from backend.database.rdb.rdb import get_db


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    return auth_service.register_user(db, data)

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_user(db, data)

@router.post("/refresh", response_model=RefreshResponse)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    return token_service.renew_token_pair(request.refresh_token, db)
    
@router.post("/logout", status_code=204)
def logout(request: LogoutRequest, db: Session = Depends(get_db),):
    return auth_service.logout_user(request.refresh_token, db)


'''
class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str
'''
