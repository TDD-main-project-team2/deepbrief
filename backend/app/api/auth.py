from fastapi import APIRouter
from backend.services.auth import auth_service, password_service, token_service

router = APIRouter(prefix="/auth", tags=["Auth"])



@router.post("/register")
def register():
    pass

@router.post("/login")
def login():
    pass

@router.post("/refresh")
def refresh():
    pass

@router.post("/logout")
def logout():
    pass