from fastapi import APIRouter
from backend.services.article import article_service

router = APIRouter(prefix="/articles", tags=["Articles"])