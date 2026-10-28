"""조직 및 조직별 리소스 조회 Repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.guideline import Guideline
from backend.models.organization import Organization
from backend.models.template import Template
from backend.models.user import User


def find_organization_by_user_id(user_id: int, db: Session) -> Organization | None:
    """사용자의 소속 조직을 조회한다."""
    return db.scalar(
        select(Organization)
        .join(User, User.organization_id == Organization.id)
        .where(User.id == user_id)
    )

def find_article_template_by_id(organization_id: int, template_id: int, db: Session) -> Template | None:
    """조직에 속한 특정 기사 템플릿을 조회한다."""
    return db.scalar(
        select(Template).where(
            Template.id == template_id,
            Template.organization_id == organization_id,
        )
    )

def find_org_guideline(organization_id: int, db: Session) -> Guideline | None:
    """조직에 속한 특정 평가 가이드라인을 조회한다."""
    return db.scalar(
        select(Guideline).where(Guideline.organization_id == organization_id)
    )

def find_all_article_templates(organization_id: int, db: Session) -> list[Template]:
    """조직에 속한 모든 기사 템플릿을 조회한다."""
    return list(
        db.scalars(
            select(Template)
            .where(Template.organization_id == organization_id)
            .order_by(Template.id.asc())
        ).all()
    )
