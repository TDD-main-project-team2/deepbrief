
def get_articles_by_user(current_user_id):
    return article_repository.find_all_by_user(current_user_id)

def get_article_by_id(article_id, current_user_id):
    # user_id check
    article = article_repository.find_article_by_id(article_id)
    if article.visibility == "Public":
        return article
    else:
        # if article.user.id is current_user_id:
        if my_article_check(article_id, current_user_id):
            return article
        else:
            raise PermissionError("접근 권한이 없습니다.")

# db 저장
def save_article(article_id, current_user_id):
    article_repository.save_article(article_id, current_user_id)

def delete_article(article_id, current_user_id):
    if my_article_check(article_id, current_user_id):
        article_repository.delete_article(article_id)


def my_article_check(article_id, current_user_id) -> bool:
    article = article_repository.find_article_by_id(article_id)
    return article.user_id == current_user_id


'''
Spring Data JPA	Python / SQLAlchemy
findById(id)	db.get(Article, id)
findAll()	db.scalars(select(Article)).all()
save(entity)	db.add(entity) + db.commit()
deleteById(id)	Fetch entity, then db.delete(entity) + db.commit()
findByUserId(id)	db.scalars(select(Article).where(Article.user_id == id)).all()
'''