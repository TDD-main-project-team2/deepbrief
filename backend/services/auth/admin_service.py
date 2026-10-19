
import secrets
import string

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.guideline import Guideline
from backend.models.template import Template
from backend.schemas.organization import OrgGuidelineRequest, OrgTemplateRequest
from backend.repositories import admin_repository, article_repository

def get_org_members(db: Session, current_user):
    return admin_repository.get_org_members(db, current_user.organization_id)


def get_org_templates(db: Session, current_user):
    return admin_repository.get_org_templates(db, current_user.organization_id)


def get_org_guidelines(db: Session, current_user):
    return admin_repository.get_org_guidelines(db, current_user.organization_id)


def update_org_code(db: Session, current_user):
    organization = admin_repository.get_organization(db, current_user.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="조직을 찾을 수 없습니다.")

    organization.code = _generate_org_code()
    try:
        db.commit()
        db.refresh(organization)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="고유한 조직 코드 생성에 실패했습니다.")

    return organization


def add_org_template(db: Session, current_user, data: OrgTemplateRequest):
    template = Template(organization_id=current_user.organization_id, title=data.title, content=data.content)
    try:
        admin_repository.add_template(db, template)
        db.commit()
        db.refresh(template)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="템플릿 생성에 실패했습니다.")
    return template


def add_org_guideline(db: Session, current_user, data: OrgGuidelineRequest):
    guideline = Guideline(organization_id=current_user.organization_id, title=data.title, content=data.content)
    try:
        admin_repository.add_guideline(db, guideline)
        db.commit()
        db.refresh(guideline)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="작성 지침 생성에 실패했습니다.")
    return guideline


def update_org_template(db: Session, current_user, template_id: int, data: OrgTemplateRequest):
    template = admin_repository.get_org_template(db, current_user.organization_id, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")

    admin_repository.update_template(db, template, data.title, data.content)
    db.commit()
    db.refresh(template)
    return template


def update_org_guideline(db: Session, current_user, guideline_id: int, data: OrgGuidelineRequest):
    guideline = admin_repository.get_org_guideline(db, current_user.organization_id, guideline_id)
    if not guideline:
        raise HTTPException(status_code=404, detail="작성 지침을 찾을 수 없습니다.")

    admin_repository.update_guideline(db, guideline, data.title, data.content)
    db.commit()
    db.refresh(guideline)
    return guideline


def update_org_article(db: Session, current_user, article_id: int, title: str | None = None, visibility: str | None = None):
    article = article_repository.get_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")
    if title is None and visibility is None:
        raise HTTPException(status_code=400, detail="수정할 기사 제목 또는 공개 범위를 입력해야 합니다.")
    if title is not None and not title.strip():
        raise HTTPException(status_code=400, detail="기사 제목은 비워둘 수 없습니다.")
    if visibility is not None and visibility not in {"private", "public"}:
        raise HTTPException(status_code=400, detail="공개 범위는 'private' 또는 'public'이어야 합니다.")

    article_repository.update_article(db, article, title=title, visibility=visibility)
    db.commit()
    db.refresh(article)
    return article


def update_org_member(db: Session, current_user, member_id: int, nickname: str, role: str | None = None):
    if role is not None and role not in {"member", "admin"}:
        raise HTTPException(status_code=400, detail="역할은 'member' 또는 'admin'이어야 합니다.")

    member = admin_repository.get_org_member(db, current_user.organization_id, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")
    if member.id == current_user.id and role is not None and role != current_user.role:
        raise HTTPException(status_code=400, detail="본인의 관리자 권한은 변경할 수 없습니다.")

    admin_repository.update_member(db, member, nickname=nickname, role=role)
    db.commit()
    db.refresh(member)
    return member


def delete_org_template(db: Session, current_user, template_id: int):
    template = admin_repository.get_org_template(db, current_user.organization_id, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    admin_repository.delete_record(db, template)
    db.commit()


def delete_org_guideline(db: Session, current_user, guideline_id: int):
    guideline = admin_repository.get_org_guideline(db, current_user.organization_id, guideline_id)
    if not guideline:
        raise HTTPException(status_code=404, detail="작성 지침을 찾을 수 없습니다.")
    admin_repository.delete_record(db, guideline)
    db.commit()

# 수정 필요
def delete_org_article(db: Session, current_user, article_id: int):
    article = article_repository.get_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")

    article_repository.delete_article(article_id, current_user.id)
    db.commit()


def delete_org_member(db: Session, current_user, member_id: int):
    if current_user.id == member_id:
        raise HTTPException(status_code=400, detail="본인 계정은 삭제할 수 없습니다.")

    member = admin_repository.get_org_member(db, current_user.organization_id, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")

    admin_repository.delete_record(db, member)
    db.commit()


def _generate_org_code(length: int = 10):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
