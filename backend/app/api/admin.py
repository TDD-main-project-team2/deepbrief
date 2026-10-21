from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_admin
from backend.database.rdb.rdb import get_db
from backend.schemas.organization import (
    OrgGuidelineRequest,
    OrgGuidelineResponse,
    OrgTemplateRequest,
    OrgTemplateResponse,
)
from backend.schemas.user import UserResponse, UserUpdate
from backend.schemas.article import ArticleResponse, ArticleListResponse, ArticleUpdate
from backend.services.auth import admin_service
from backend.services.resources import article_service, organization_service


router = APIRouter(prefix="/admin", tags=["Admin"],)


@router.get("/members", response_model=list[UserResponse])
def get_org_members(db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return admin_service.get_org_members(db, current_user)


@router.get("/templates", response_model=list[OrgTemplateResponse])
def get_org_templates(db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return organization_service.get_all_organization_article_templates(current_user.id, db)


@router.get("/guidelines", response_model=list[OrgGuidelineResponse])
def get_org_guidelines(db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return admin_service.get_org_guidelines(db, current_user)


@router.get("/articles", response_model=ArticleListResponse)
def get_org_articles(db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return article_service.get_all_articles_by_org_id(db, current_user)


@router.post("/templates", response_model=OrgTemplateResponse)
def add_org_template(data: OrgTemplateRequest, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return admin_service.add_org_template(db, current_user, data)


@router.post("/guidelines", response_model=OrgGuidelineResponse)
def add_org_guideline(data: OrgGuidelineRequest, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return admin_service.add_org_guideline(db, current_user, data)


@router.patch("/code")
def update_org_code(db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return admin_service.update_org_code(db, current_user)


@router.patch("/templates/{template_id}", response_model=OrgTemplateResponse)
def update_org_template(template_id: int, data: OrgTemplateRequest, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return admin_service.update_org_template(db, current_user, template_id, data)


@router.patch("/guidelines/{guideline_id}", response_model=OrgGuidelineResponse)
def update_org_guideline(guideline_id: int, data: OrgGuidelineRequest, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return admin_service.update_org_guideline(db, current_user, guideline_id, data)


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
def update_org_article(article_id: int, data: ArticleUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return admin_service.update_org_article(db, data, article_id)


@router.patch("/members/{member_id}", response_model=UserResponse)
def update_org_member(member_id: int, data: UserUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    return admin_service.update_org_member(db, current_user, member_id, data)


@router.delete("/templates/{template_id}", status_code=204)
def delete_org_template(template_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    admin_service.delete_org_template(db, current_user, template_id)


@router.delete("/guidelines/{guideline_id}", status_code=204)
def delete_org_guideline(guideline_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    admin_service.delete_org_guideline(db, current_user, guideline_id)


@router.delete("/articles/{article_id}", status_code=204)
def delete_org_article(article_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    admin_service.delete_org_article(db, current_user, article_id)


@router.delete("/members/{member_id}", status_code=204)
def delete_org_member(member_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    admin_service.delete_org_member(db, current_user, member_id)