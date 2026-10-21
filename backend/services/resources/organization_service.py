from sqlalchemy.orm import Session

from backend.app.dependencies import _not_found, ensure_organization_member
from backend.repositories import organization_repository


def get_organization_by_user_id(user_id: int, db: Session):
    organization = organization_repository.find_organization_by_user_id(
        user_id, db
    )

    if organization is None:
        raise _not_found()

    ensure_organization_member(organization.id, user_id, db)
    return organization

def get_organization_article_template_for_user(user_id: int, template_id: int, db: Session):
    org = get_organization_by_user_id(user_id, db)
    return organization_repository.find_article_template_by_id(
        org.id, template_id, db
    )

def get_organization_evaluation_guideline_for_user(user_id: int, db: Session):
    org = get_organization_by_user_id(user_id, db)
    return organization_repository.find_org_guideline(
        org.id, db
    )

def get_all_organization_article_templates(user_id: int, db: Session):
    org = get_organization_by_user_id(user_id, db)
    return organization_repository.find_all_article_templates(org.id, db)