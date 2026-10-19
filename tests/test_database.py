import os
import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.database.vector.vector_db import vector_db
from backend.models.article import Article
from backend.models.article_chunk import ArticleChunk
from backend.models.conversation import Conversation
from backend.models.guideline import Guideline
from backend.models.message import Message
from backend.models.organization import Organization
from backend.models.template import Template
from backend.models.user import User
from backend.models.user_article import UserArticle
from backend.repositories import (
    article_repository,
    conversation_repository,
    message_repository,
    organization_repository,
    refresh_token_repository,
    user_repository,
)

load_dotenv()
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="DB 테스트는 TEST_DATABASE_URL이 있을 때만 실행",
)


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine, monkeypatch):
    """
    테스트마다 트랜잭션을 열고 끝나면 롤백해 DB에 아무것도 남기지 않는다.
    Repository 안의 commit은 세이브포인트만 확정하므로 바깥 트랜잭션과 함께 롤백된다.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        test_session = sessionmaker(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        for repository in (article_repository, conversation_repository, message_repository):
            monkeypatch.setattr(repository, "SessionLocal", test_session)
        monkeypatch.setattr(vector_db, "SessionLocal", test_session)

        session = test_session()
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


def unique(prefix):
    """다른 데이터와 겹치지 않는 값을 만든다."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def save(db, row):
    db.add(row)
    db.flush()
    return row


def count(db, model, *conditions):
    return db.scalar(select(func.count()).select_from(model).where(*conditions))


def make_organization(db, code=None):
    return save(db, Organization(name="새봄신문", code=code or unique("ORG")))


def make_user(db, organization, email=None):
    return save(db, User(
        organization_id=organization.id,
        nickname="김바다",
        email=email or f"{unique('reporter')}@example.com",
        password_hash="hashed-password",
    ))


def make_article(db, **fields):
    values = {
        "content_hash": unique("hash"),
        "title": "한빛시 전기버스 도입",
        "body": "한빛시는 내년 3월부터 시내버스 120대를 전기버스로 바꾼다.",
    }
    values.update(fields)
    return save(db, Article(**values))


def link(db, user, article):
    save(db, UserArticle(user_id=user.id, article_id=article.id))


def make_conversation(db, user, article):
    return save(db, Conversation(user_id=user.id, article_id=article.id, title="전기버스 질문"))


def make_template(db, organization):
    return save(db, Template(organization_id=organization.id, title="보도자료", content="제목과 본문"))


def embedding(first, second):
    """앞의 두 값만 다른 1024차원 벡터를 만든다 (코사인 거리 비교용)."""
    return [first, second] + [0.0] * 1022


def make_chunk(article, index, content, vector=None):
    return ArticleChunk(
        article_id=article.id,
        chunk_index=index,
        content=content,
        embedding=vector or embedding(1.0, 0.0),
    )


def test_article_duplicate_content_hash(db):
    """같은 content_hash로 기사를 두 번 저장할 수 없다."""
    article = make_article(db)

    with pytest.raises(IntegrityError):
        make_article(db, content_hash=article.content_hash)


def test_article_blank_title(db):
    """공백뿐인 제목은 저장할 수 없다."""
    with pytest.raises(IntegrityError):
        make_article(db, title="   ")


def test_article_invalid_visibility(db):
    """visibility는 private, public만 저장할 수 있다."""
    with pytest.raises(IntegrityError):
        make_article(db, visibility="draft")


def test_user_duplicate_email(db):
    """같은 이메일로 사용자를 두 번 저장할 수 없다."""
    organization = make_organization(db)
    user = make_user(db, organization)

    with pytest.raises(IntegrityError):
        make_user(db, organization, email=user.email)


def test_organization_duplicate_code(db):
    """같은 조직 코드로 조직을 두 번 저장할 수 없다."""
    organization = make_organization(db)

    with pytest.raises(IntegrityError):
        make_organization(db, code=organization.code)


def test_message_invalid_role(db):
    """메시지 role은 user, assistant만 저장할 수 있다."""
    organization = make_organization(db)
    conversation = make_conversation(db, make_user(db, organization), make_article(db))

    with pytest.raises(IntegrityError):
        save(db, Message(conversation_id=conversation.id, role="system", content="안녕하세요"))


def test_article_chunk_duplicate_index(db):
    """한 기사에 같은 chunk_index를 두 번 저장할 수 없다."""
    article = make_article(db)
    save(db, make_chunk(article, 0, "첫 번째 조각"))

    with pytest.raises(IntegrityError):
        save(db, make_chunk(article, 0, "같은 번호의 조각"))


def test_article_chunk_negative_index(db):
    """chunk_index는 음수로 저장할 수 없다."""
    article = make_article(db)

    with pytest.raises(IntegrityError):
        save(db, make_chunk(article, -1, "음수 번호의 조각"))


def test_conversation_duplicate_user_article(db):
    """같은 사용자와 기사로 대화를 두 번 만들 수 없다."""
    user = make_user(db, make_organization(db))
    article = make_article(db)
    make_conversation(db, user, article)

    with pytest.raises(IntegrityError):
        make_conversation(db, user, article)


def test_message_without_conversation(db):
    """없는 대화에는 메시지를 저장할 수 없다."""
    with pytest.raises(IntegrityError):
        save(db, Message(conversation_id=-1, role="user", content="안녕하세요"))


def test_user_without_organization(db):
    """없는 조직에는 사용자를 저장할 수 없다."""
    with pytest.raises(IntegrityError):
        save(db, User(
            organization_id=-1,
            nickname="김바다",
            email=f"{unique('reporter')}@example.com",
            password_hash="hashed-password",
        ))


def test_add_article_to_user_ignores_duplicate(db):
    """이미 연결된 기사를 다시 연결해도 연결은 하나만 남는다."""
    user = make_user(db, make_organization(db))
    article = make_article(db)

    article_repository.add_article_to_user(user.id, article.id)
    article_repository.add_article_to_user(user.id, article.id)

    assert count(db, UserArticle, UserArticle.user_id == user.id) == 1


def test_delete_article_removes_only_link(db):
    """기사 삭제는 사용자와의 연결만 지우고 기사는 남기며, 연결이 없으면 False를 반환한다."""
    user = make_user(db, make_organization(db))
    article = make_article(db)
    link(db, user, article)

    assert article_repository.delete_article(article.id, user.id) is True
    assert count(db, UserArticle, UserArticle.article_id == article.id) == 0
    assert count(db, Article, Article.id == article.id) == 1
    assert article_repository.delete_article(article.id, user.id) is False


def test_find_all_by_user_returns_linked_articles(db):
    """사용자와 연결된 기사만 id 순서로 조회한다."""
    user = make_user(db, make_organization(db))
    first = make_article(db)
    second = make_article(db)
    make_article(db)
    link(db, user, second)
    link(db, user, first)

    articles = article_repository.find_all_by_user(user.id)

    assert [article.id for article in articles] == [first.id, second.id]


def test_user_has_access(db):
    """기사와 연결된 사용자만 접근할 수 있다."""
    organization = make_organization(db)
    owner = make_user(db, organization)
    other = make_user(db, organization)
    article = make_article(db)
    link(db, owner, article)

    assert article_repository.user_has_access(db, owner.id, article.id) is True
    assert article_repository.user_has_access(db, other.id, article.id) is False


def test_get_by_content_hash(db):
    """content_hash로 기사를 찾고, 없는 값이면 None을 반환한다."""
    article = make_article(db)

    assert article_repository.get_by_content_hash(db, article.content_hash).id == article.id
    assert article_repository.get_by_content_hash(db, unique("hash")) is None


def test_article_create_and_find_by_id(db):
    """기사를 저장하고 id로 다시 찾는다."""
    article = Article(content_hash=unique("hash"), title="한빛시 전기버스 도입", body="버스를 바꾼다.")

    created = article_repository.create(db, article)

    assert article_repository.find_article_by_id(created.id).title == "한빛시 전기버스 도입"


def test_find_article_by_conversation_id(db):
    """대화 id로 그 대화의 기사를 찾는다."""
    article = make_article(db)
    conversation = make_conversation(db, make_user(db, make_organization(db)), article)

    assert article_repository.find_article_by_conversation_id(conversation.id).id == article.id


def test_update_category(db):
    """기사의 카테고리를 바꾸고, 없는 기사면 아무것도 하지 않는다."""
    article = make_article(db)

    article_repository.update_category(article.id, "교통")
    article_repository.update_category(-1, "교통")

    assert db.scalar(select(Article.category).where(Article.id == article.id)) == "교통"


def test_conversation_create_and_find_by_id(db):
    """대화를 만들고 id로 다시 찾는다."""
    user = make_user(db, make_organization(db))
    article = make_article(db)

    conversation = conversation_repository.create_conversation("전기버스 질문", user.id, article.id)

    found = conversation_repository.find_conversation_by_id(conversation.id)
    assert (found.user_id, found.article_id, found.title) == (user.id, article.id, "전기버스 질문")


def test_find_all_conversations_by_user(db):
    """사용자의 대화만 id 순서로 조회한다."""
    organization = make_organization(db)
    user = make_user(db, organization)
    first = make_conversation(db, user, make_article(db))
    second = make_conversation(db, user, make_article(db))
    make_conversation(db, make_user(db, organization), make_article(db))

    conversations = conversation_repository.find_all_by_user(user.id)

    assert [conversation.id for conversation in conversations] == [first.id, second.id]


def test_delete_conversation_removes_messages(db):
    """대화를 삭제하면 그 대화의 메시지도 함께 삭제된다."""
    conversation = make_conversation(db, make_user(db, make_organization(db)), make_article(db))
    save(db, Message(conversation_id=conversation.id, role="user", content="질문"))
    save(db, Message(conversation_id=conversation.id, role="assistant", content="답변"))

    conversation_repository.delete_conversation(conversation.id)

    assert count(db, Conversation, Conversation.id == conversation.id) == 0
    assert count(db, Message, Message.conversation_id == conversation.id) == 0


def test_find_recent_by_conversation_order_and_limit(db):
    """최근 메시지를 limit개만 가져와 오래된 순서로 반환한다."""
    conversation = make_conversation(db, make_user(db, make_organization(db)), make_article(db))
    for content in ["첫 번째", "두 번째", "세 번째", "네 번째"]:
        save(db, Message(conversation_id=conversation.id, role="user", content=content))

    messages = message_repository.find_recent_by_conversation(conversation.id, limit=3)

    assert [message.content for message in messages] == ["두 번째", "세 번째", "네 번째"]


def test_message_create_find_and_delete(db):
    """메시지를 저장하고 id로 찾은 뒤 삭제한다."""
    conversation = make_conversation(db, make_user(db, make_organization(db)), make_article(db))

    message = message_repository.create_message(conversation.id, "버스는 몇 대인가요?", "user")
    assert message_repository.find_message_by_id(message.id).content == "버스는 몇 대인가요?"

    message_repository.delete_message(message.id)
    assert message_repository.find_message_by_id(message.id) is None


def test_find_organization_by_user_id(db):
    """사용자의 소속 조직을 찾는다."""
    organization = make_organization(db)
    user = make_user(db, organization)

    found = organization_repository.find_organization_by_user_id(user.id, db)
    assert found.id == organization.id


def test_find_all_article_templates_other_organization(db):
    """자기 조직의 템플릿만 id 순서로 조회하고 다른 조직의 템플릿은 제외한다."""
    own = make_organization(db)
    first = make_template(db, own)
    second = make_template(db, own)
    make_template(db, make_organization(db))

    templates = organization_repository.find_all_article_templates(own.id, db)

    assert [template.id for template in templates] == [first.id, second.id]


def test_find_article_template_by_id_other_organization(db):
    """다른 조직의 템플릿은 조회되지 않는다."""
    own = make_organization(db)
    other = make_organization(db)
    template = make_template(db, other)

    assert organization_repository.find_article_template_by_id(own.id, template.id, db) is None
    found = organization_repository.find_article_template_by_id(other.id, template.id, db)
    assert found.id == template.id


def test_find_org_guideline_by_id_other_organization(db):
    """다른 조직의 가이드라인은 조회되지 않는다."""
    own = make_organization(db)
    other = make_organization(db)
    guideline = save(db, Guideline(organization_id=other.id, title="표기 원칙", content="숫자 표기"))

    assert organization_repository.find_org_guideline_by_id(own.id, guideline.id, db) is None
    found = organization_repository.find_org_guideline_by_id(other.id, guideline.id, db)
    assert found.id == guideline.id


def test_user_create_and_get_by_id(db):
    """사용자를 저장하고 id로 다시 찾는다."""
    organization = make_organization(db)
    user = User(
        organization_id=organization.id,
        nickname="김바다",
        email=f"{unique('reporter')}@example.com",
        password_hash="hashed-password",
    )

    created = user_repository.create(db, user)
    db.expunge_all()   # 세션 캐시가 아니라 DB에서 다시 읽게 한다

    assert user_repository.get_by_id(db, created.id).email == user.email


def test_get_by_email(db):
    """이메일로 사용자를 찾고, 없는 이메일이면 None을 반환한다."""
    user = make_user(db, make_organization(db))

    assert user_repository.get_by_email(db, user.email).id == user.id
    assert user_repository.get_by_email(db, f"{unique('nobody')}@example.com") is None


def test_get_organization_by_code(db):
    """조직 코드로 조직을 찾고, 없는 코드면 None을 반환한다."""
    organization = make_organization(db)

    assert user_repository.get_organization_by_code(db, organization.code).id == organization.id
    assert user_repository.get_organization_by_code(db, unique("ORG")) is None


def test_refresh_token_create_stores_hash(db):
    """리프레시 토큰은 원문이 아니라 sha256 해시로 저장된다."""
    user = make_user(db, make_organization(db))
    token = unique("token")
    expired_at = datetime.now(timezone.utc) + timedelta(days=7)

    record = refresh_token_repository.create(db, user.id, token, expired_at)

    assert record.token_hash == sha256(token.encode("utf-8")).hexdigest()
    assert record.token_hash != token


def test_refresh_token_get_and_delete_by_token(db):
    """토큰 원문으로 조회하고 삭제할 수 있다."""
    user = make_user(db, make_organization(db))
    token = unique("token")
    expired_at = datetime.now(timezone.utc) + timedelta(days=7)
    record = refresh_token_repository.create(db, user.id, token, expired_at)

    assert refresh_token_repository.get_by_token(db, token).id == record.id

    refresh_token_repository.delete_by_token(db, token)

    assert refresh_token_repository.get_by_token(db, token) is None


def test_refresh_token_delete_expired(db):
    """만료된 토큰만 삭제하고 유효한 토큰은 남긴다."""
    user = make_user(db, make_organization(db))
    now = datetime.now(timezone.utc)
    expired = unique("token")
    valid = unique("token")
    refresh_token_repository.create(db, user.id, expired, now - timedelta(days=1))
    refresh_token_repository.create(db, user.id, valid, now + timedelta(days=7))

    refresh_token_repository.delete_expired(db)

    assert refresh_token_repository.get_by_token(db, expired) is None
    assert refresh_token_repository.get_by_token(db, valid) is not None


def test_replace_article_chunks_replaces_old_chunks(db):
    """기사의 기존 청크를 지우고 새 청크로 바꾼다."""
    article = make_article(db)
    save(db, make_chunk(article, 0, "기존 첫 번째 조각"))
    save(db, make_chunk(article, 1, "기존 두 번째 조각"))

    vector_db.replace_article_chunks(article.id, [make_chunk(article, 0, "새 조각")])

    chunks = vector_db.get_article_chunks(article.id)
    assert [chunk.content for chunk in chunks] == ["새 조각"]


def test_replace_article_chunks_rollback_on_failure(db):
    """새 청크 저장에 실패하면 삭제도 취소되어 기존 청크가 남는다."""
    article = make_article(db)
    save(db, make_chunk(article, 0, "기존 조각"))
    broken = [make_chunk(article, 0, "새 조각"), make_chunk(article, 0, "같은 번호의 조각")]

    with pytest.raises(IntegrityError):
        vector_db.replace_article_chunks(article.id, broken)

    chunks = vector_db.get_article_chunks(article.id)
    assert [chunk.content for chunk in chunks] == ["기존 조각"]


def test_updated_at_trigger(db):
    """행을 수정하면 트리거가 updated_at을 수정 시각으로 바꾼다."""
    article = make_article(db)
    db.refresh(article)

    article.title = "한빛시 전기버스 도입 연기"
    db.flush()
    db.refresh(article)

    assert article.updated_at > article.created_at


def test_search_article_chunks_orders_by_distance(db):
    """현재 기사의 청크만 질문 벡터와 가까운 순서로 반환한다."""
    article = make_article(db)
    other = make_article(db)
    save(db, make_chunk(article, 0, "먼 조각", embedding(0.0, 1.0)))
    save(db, make_chunk(article, 1, "가까운 조각", embedding(1.0, 0.0)))
    save(db, make_chunk(article, 2, "중간 조각", embedding(1.0, 1.0)))
    save(db, make_chunk(other, 0, "다른 기사 조각", embedding(1.0, 0.0)))

    chunks = vector_db.search_article_chunks(embedding(1.0, 0.0), article.id)

    assert [chunk.content for chunk in chunks] == ["가까운 조각", "중간 조각", "먼 조각"]


def test_search_organization_chunks_excludes_current_and_other_org(db):
    """같은 조직의 다른 기사 청크만 찾고, 현재 기사와 다른 조직의 청크는 제외한다."""
    own_user = make_user(db, make_organization(db))
    other_user = make_user(db, make_organization(db))
    current = make_article(db)
    same_org = make_article(db)
    other_org = make_article(db)
    link(db, own_user, current)
    link(db, own_user, same_org)
    link(db, other_user, other_org)
    save(db, make_chunk(current, 0, "현재 기사 조각"))
    save(db, make_chunk(same_org, 0, "같은 조직 기사 조각"))
    save(db, make_chunk(other_org, 0, "다른 조직 기사 조각"))

    chunks = vector_db.search_organization_chunks(embedding(1.0, 0.0), current.id)

    assert [chunk.content for chunk in chunks] == ["같은 조직 기사 조각"]


def test_search_organization_chunks_without_organization(db):
    """어떤 사용자와도 연결되지 않은 기사는 조직을 찾을 수 없어 ValueError가 난다."""
    article = make_article(db)

    with pytest.raises(ValueError):
        vector_db.search_organization_chunks(embedding(1.0, 0.0), article.id)
