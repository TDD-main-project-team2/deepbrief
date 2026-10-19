from sqlalchemy.orm import Session
from backend.repositories import article_repository
from backend.app.dependencies import ensure_article_access, _not_found
from backend.services.ai import model_service
from backend.services.rag import rag_service


def find_article_by_id(article_id):
    article = article_repository.find_article_by_id(article_id)
    if article is None:
        raise _not_found()
    return article

def get_articles_by_user(current_user_id):
    return article_repository.find_all_by_user(current_user_id)

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

def delete_article(article_id, current_user_id):
    article = find_article_by_id(article_id)
    ensure_owner(article.user_id, current_user_id)
    deleted = article_repository.delete_article(
        article_id,
        current_user_id,
    )

    if not deleted:
        raise _not_found()

def categorize_article(article_id):
    article = find_article_by_id(article_id)
    source = f"{article.title}\n{article.body.split(chr(10) + chr(10))[0]}"

    chunks = rag_service.retrieve_similar_article_chunks(source, article_id, 5)
    context = rag_service.build_context(chunks)

    category = model_service.generate_category(context)
    article_repository.update_category(article_id, category)

    return category
'''
def save_article(article_id, current_user_id):
    article_repository.save_article(article_id, current_user_id)

def favorite_article_toggle():
    pass

def delete_article(article_id, current_user_id):
    if my_article_check(article_id, current_user_id):
        article_repository.delete_article(article_id)

def my_article_check(article_id, current_user_id) -> bool:
    article = article_repository.find_article_by_id(article_id)
    return article.user_id == current_user_id
'''


'''
Spring Data JPA	Python / SQLAlchemy
findById(id)	db.get(Article, id)
findAll()	db.scalars(select(Article)).all()
save(entity)	db.add(entity) + db.commit()
deleteById(id)	Fetch entity, then db.delete(entity) + db.commit()
findByUserId(id)	db.scalars(select(Article).where(Article.user_id == id)).all()
'''
