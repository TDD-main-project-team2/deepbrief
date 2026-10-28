from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.rdb.rdb import get_db
from backend.app.dependencies import get_current_user
from backend.services.resources import organization_service
from backend.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return organization_service.get_user_profile(db, current_user)