from sqlalchemy.orm import Session
from backend.repositories import article_repository
from backend.app.dependencies import ensure_article_access, _not_found
from backend.services.resources import conversation_service


def find_article_by_id(article_id):
    article = article_repository.find_article_by_id(article_id)
    if article is None:
        raise _not_found()
    return article

def get_all_articles_by_org_id(db: Session, current_user):
    articles = article_repository.find_all_by_org(db, current_user.organization_id)

    return {
        "articles": articles,
        "total": len(articles),
    }

def get_all_public_articles_by_org_id(current_user, db):
    articles = article_repository.find_all_public_by_org(db, current_user.organization_id)

    return {
        "articles": articles,
        "total": len(articles),
    }

def get_articles_by_user(current_user_id):
    articles = article_repository.find_all_by_user(current_user_id)
    return {
        "articles": articles,
        "total": len(articles),
    }

def get_article_by_id(article_id, current_user_id, db):
    article = find_article_by_id(article_id)
    if article.visibility == "public":
        return article
    ensure_article_access(article_id, current_user_id, db)
    return article

def get_article_by_conversation_id(conversation_id, current_user_id, db: Session):
    article = article_repository.find_article_by_conversation_id(conversation_id)
    if article is None:
        raise _not_found()
    
    if article.visibility == "public":
        return article
    ensure_article_access(article.id, current_user_id, db)
    return article

def delete_article(article_id, current_user_id, db: Session):
    article = find_article_by_id(article_id)    
    if article.visibility == "private":
        ensure_article_access(article_id, current_user_id, db)
        deleted = article_repository.delete_article_associations(article_id, db)
    else:
        deleted = article_repository.delete_article_association(
            article_id,
            current_user_id,
            db
        )
    if not deleted:
        raise _not_found()
    
    db.commit()