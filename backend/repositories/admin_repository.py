from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.article import Article
from backend.models.user_article import UserArticle
from backend.models.guideline import Guideline
from backend.models.organization import Organization
from backend.models.template import Template
from backend.models.user import User
from backend.models.conversation import Conversation


def get_org_members(db: Session, organization_id: int):
    return db.scalars(select(User).where(User.organization_id == organization_id)).all()


def get_org_templates(db: Session, organization_id: int):
    return db.scalars(select(Template).where(Template.organization_id == organization_id)).all()


def get_org_guidelines(db: Session, organization_id: int):
    return db.scalars(select(Guideline).where(Guideline.organization_id == organization_id)).all()


def get_org_template(db: Session, organization_id: int, template_id: int):
    return db.scalar(select(Template).where(Template.id == template_id, Template.organization_id == organization_id))


def get_org_guideline(db: Session, organization_id: int, guideline_id: int):
    return db.scalar(select(Guideline).where(Guideline.id == guideline_id, Guideline.organization_id == organization_id))


def get_org_member(db: Session, organization_id: int, member_id: int):
    return db.scalar(select(User).where(User.id == member_id, User.organization_id == organization_id))


def get_organization(db: Session, organization_id: int):
    return db.get(Organization, organization_id)


def add_template(db: Session, template: Template):
    db.add(template)
    db.flush()
    return template


def add_guideline(db: Session, guideline: Guideline):
    db.add(guideline)
    db.flush()
    return guideline


def update_template(db: Session, template: Template, title: str, content: str):
    template.title = title
    template.content = content
    db.flush()
    return template


def update_guideline(db: Session, guideline: Guideline, title: str, content: str):
    guideline.title = title
    guideline.content = content
    db.flush()
    return guideline


def update_member(db: Session, member: User, nickname: str | None = None, role: str | None = None):
    if nickname is not None:
        member.nickname = nickname
    if role is not None:
        member.role = role
    db.flush()
    return member


def delete_record(db: Session, record):
    db.delete(record)
    db.flush()

def delete_record(db: Session, record):
    if isinstance(record, User):
        db.query(Conversation).filter(Conversation.user_id == record.id).delete()

        private_article_ids = db.scalars(
            select(UserArticle.article_id)
            .join(Article, Article.id == UserArticle.article_id)
            .where(UserArticle.user_id == record.id, Article.visibility == "private")
        ).all()

        if private_article_ids:
            db.query(Article).filter(Article.id.in_(private_article_ids)).delete(synchronize_session=False)

        db.query(UserArticle).filter(UserArticle.user_id == record.id).delete()

    db.delete(record)
    db.flush()