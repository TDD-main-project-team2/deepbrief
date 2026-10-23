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
    admin_repository,
    article_repository,
    conversation_repository,
    message_repository,
    organization_repository,
    refresh_token_repository,
    user_repository,
)
from backend.services.agent import tools

load_dotenv()
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
KST = timezone(timedelta(hours=9))

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


def make_organization(db, code=None, admin_code=None):
    return save(db, Organization(
        name="새봄신문",
        code=code or unique("ORG"),
        admin_code=admin_code or unique("ADMIN"),
    ))


def make_user(db, organization, email=None, role="member"):
    return save(db, User(
        organization_id=organization.id,
        role=role,
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


def test_organization_duplicate_admin_code(db):
    """같은 관리자 코드로 조직을 두 번 저장할 수 없다."""
    organization = make_organization(db)

    with pytest.raises(IntegrityError):
        make_organization(db, admin_code=organization.admin_code)


def test_organization_blank_admin_code(db):
    """공백뿐인 관리자 코드는 저장할 수 없다."""
    with pytest.raises(IntegrityError):
        make_organization(db, admin_code="   ")


def test_message_invalid_role(db):
    """메시지 role은 user, assistant만 저장할 수 있다."""
    organization = make_organization(db)
    conversation = make_conversation(db, make_user(db, organization), make_article(db))

    with pytest.raises(IntegrityError):
        save(db, Message(conversation_id=conversation.id, role="system", content="안녕하세요"))


def test_user_invalid_role(db):
    """사용자 role은 member, admin만 저장할 수 있다."""
    organization = make_organization(db)
    make_user(db, organization, role="admin")

    with pytest.raises(IntegrityError):
        make_user(db, organization, role="owner")


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


def test_delete_article_association_removes_user_data(db):
    """한 사용자의 연결·대화·메시지만 지우고 기사와 다른 사용자 것은 남기며, 연결이 없으면 False."""
    organization = make_organization(db)
    user = make_user(db, organization)
    other = make_user(db, organization)
    article = make_article(db, visibility="public")
    link(db, user, article)
    link(db, other, article)
    mine = make_conversation(db, user, article)
    theirs = make_conversation(db, other, article)
    save(db, Message(conversation_id=mine.id, role="user", content="질문"))
    save(db, Message(conversation_id=theirs.id, role="user", content="질문"))

    assert article_repository.delete_article_association(article.id, user.id, db) is True
    db.flush()   # 서비스가 commit하는 자리

    assert count(db, UserArticle, UserArticle.article_id == article.id) == 1
    assert count(db, Conversation, Conversation.id == mine.id) == 0
    assert count(db, Message, Message.conversation_id == mine.id) == 0
    assert count(db, Message, Message.conversation_id == theirs.id) == 1
    assert count(db, Article, Article.id == article.id) == 1
    assert article_repository.delete_article_association(article.id, user.id, db) is False


def test_delete_article_associations_removes_article(db):
    """기사의 메시지·대화·연결·청크와 기사를 모두 지우고, 없는 기사면 False를 반환한다."""
    organization = make_organization(db)
    first = make_user(db, organization)
    second = make_user(db, organization)
    article = make_article(db)
    other = make_article(db)
    link(db, first, article)
    link(db, second, article)
    link(db, first, other)
    conversations = [make_conversation(db, first, article), make_conversation(db, second, article)]
    for conversation in conversations:
        save(db, Message(conversation_id=conversation.id, role="user", content="질문"))
    save(db, make_chunk(article, 0, "삭제할 기사 조각"))
    save(db, make_chunk(other, 0, "남을 기사 조각"))

    assert article_repository.delete_article_associations(article.id, db) is True
    db.flush()

    ids = [conversation.id for conversation in conversations]
    assert count(db, Message, Message.conversation_id.in_(ids)) == 0
    assert count(db, Conversation, Conversation.article_id == article.id) == 0
    assert count(db, UserArticle, UserArticle.article_id == article.id) == 0
    assert count(db, ArticleChunk, ArticleChunk.article_id == article.id) == 0
    assert count(db, Article, Article.id == article.id) == 0
    assert count(db, ArticleChunk, ArticleChunk.article_id == other.id) == 1
    assert count(db, UserArticle, UserArticle.article_id == other.id) == 1
    assert article_repository.delete_article_associations(article.id, db) is False


def test_find_all_by_org_shared_article_once(db):
    """조직 구성원이 가진 기사를 한 번씩만 조회하고, 다른 조직의 기사는 제외한다."""
    own = make_organization(db)
    first = make_user(db, own)
    second = make_user(db, own)
    shared = make_article(db)
    single = make_article(db)
    link(db, first, shared)
    link(db, second, shared)
    link(db, second, single)
    link(db, make_user(db, make_organization(db)), make_article(db))

    articles = article_repository.find_all_by_org(db, own.id)

    assert sorted(article.id for article in articles) == sorted([shared.id, single.id])


def test_find_all_public_by_org(db):
    """조직 구성원이 가진 기사 중 공개 기사만 조회한다."""
    user = make_user(db, make_organization(db))
    public = make_article(db, visibility="public")
    link(db, user, public)
    link(db, user, make_article(db, visibility="private"))

    articles = article_repository.find_all_public_by_org(db, user.organization_id)

    assert [article.id for article in articles] == [public.id]


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


def test_get_by_content_hash_and_org_id(db):
    organization = make_organization(db)
    user = make_user(db, organization)
    other_organization = make_organization(db)
    article = make_article(db)

    link(db, user, article)

    # 기사가 연결된 조직에서는 조회된다.
    found = article_repository.get_by_content_hash_and_org_id(
        db, organization.id, article.content_hash
    )
    assert found is not None
    assert found.id == article.id

    # 다른 조직에서는 조회되지 않는다.
    not_found = article_repository.get_by_content_hash_and_org_id(
        db, other_organization.id, article.content_hash
    )
    assert not_found is None

    # 존재하지 않는 해시도 조회되지 않는다.
    missing = article_repository.get_by_content_hash_and_org_id(
        db, organization.id, unique("hash")
    )
    assert missing is None


def test_article_create_and_find_by_id(db):
    """기사를 저장하고 id로 다시 찾는다."""
    article = Article(content_hash=unique("hash"), title="한빛시 전기버스 도입", body="버스를 바꾼다.")

    created = article_repository.create(db, article)

    assert article_repository.find_article_by_id(created.id, db).title == "한빛시 전기버스 도입"


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


def test_create_conversation_returns_existing(db):
    """같은 사용자와 기사로 다시 만들면 기존 대화를 돌려주고 대화는 하나만 남는다."""
    user = make_user(db, make_organization(db))
    article = make_article(db)

    first = conversation_repository.create_conversation("전기버스 질문", user.id, article.id)
    second = conversation_repository.create_conversation("다른 제목", user.id, article.id)

    assert second.id == first.id
    assert count(db, Conversation, Conversation.user_id == user.id) == 1


def test_find_all_conversations_by_user(db):
    """사용자의 대화만 id 순서로 조회한다."""
    organization = make_organization(db)
    user = make_user(db, organization)
    first = make_conversation(db, user, make_article(db))
    second = make_conversation(db, user, make_article(db))
    make_conversation(db, make_user(db, organization), make_article(db))

    conversations = conversation_repository.find_all_by_user(user.id)

    assert [conversation.id for conversation in conversations] == [first.id, second.id]


def test_find_conversation_by_article_id(db):
    """기사 id로 대화를 찾고, 대화가 없는 기사면 None을 반환한다."""
    article = make_article(db)
    conversation = make_conversation(db, make_user(db, make_organization(db)), article)

    found = conversation_repository.find_conversation_by_article_id(article.id)
    assert found.id == conversation.id
    assert conversation_repository.find_conversation_by_article_id(make_article(db).id) is None


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


def test_find_messages_by_conversation_id_order(db):
    """그 대화의 메시지만 id 순서로 조회한다."""
    user = make_user(db, make_organization(db))
    conversation = make_conversation(db, user, make_article(db))
    other = make_conversation(db, user, make_article(db))
    save(db, Message(conversation_id=conversation.id, role="user", content="질문"))
    save(db, Message(conversation_id=conversation.id, role="assistant", content="답변"))
    save(db, Message(conversation_id=other.id, role="user", content="다른 대화 질문"))

    messages = message_repository.find_messages_by_conversation_id(conversation.id)

    assert [message.content for message in messages] == ["질문", "답변"]


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


def test_find_org_guideline_other_organization(db):
    """자기 조직의 가이드라인을 찾고, 다른 조직 것은 제외하며, 없으면 None을 반환한다."""
    own = make_organization(db)
    other = make_organization(db)
    guideline = save(db, Guideline(organization_id=own.id, title="표기 원칙", content="숫자 표기"))
    save(db, Guideline(organization_id=other.id, title="다른 조직 지침", content="내용"))

    assert organization_repository.find_org_guideline(own.id, db).id == guideline.id
    assert organization_repository.find_org_guideline(make_organization(db).id, db) is None


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


def test_get_by_article_id(db):
    """기사와 연결된 사용자를 찾고, 연결이 없는 기사면 None을 반환한다."""
    user = make_user(db, make_organization(db))
    article = make_article(db)
    link(db, user, article)

    assert user_repository.get_by_article_id(db, article.id).id == user.id
    assert user_repository.get_by_article_id(db, make_article(db).id) is None


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


def test_get_article_chunks_order(db):
    """그 기사의 청크만 chunk_index 순서로 조회한다."""
    article = make_article(db)
    save(db, make_chunk(article, 1, "두 번째 조각"))
    save(db, make_chunk(article, 0, "첫 번째 조각"))
    save(db, make_chunk(make_article(db), 0, "다른 기사 조각"))

    chunks = vector_db.get_article_chunks(article.id)

    assert [chunk.content for chunk in chunks] == ["첫 번째 조각", "두 번째 조각"]


# 사내 데이터 조회 SQL (services/agent/tools.py)
# 안쪽 조회 함수는 session을 인자로 받으므로 db를 그대로 넘긴다. LLM이 도구를 고르는 부분은 다루지 않는다.


def test_find_organization_id(db):
    """기사를 가진 사용자의 조직을 찾고, 연결이 없거나 조직이 여러 개면 None을 반환한다."""
    own = make_organization(db)
    shared = make_article(db)
    link(db, make_user(db, own), shared)
    link(db, make_user(db, own), shared)
    cross = make_article(db)
    link(db, make_user(db, own), cross)
    link(db, make_user(db, make_organization(db)), cross)

    assert tools._find_organization_id(db, shared.id) == own.id
    assert tools._find_organization_id(db, make_article(db).id) is None
    assert tools._find_organization_id(db, cross.id) is None


def test_count_articles_counts_shared_article_once(db):
    """조직 안 여러 명이 가진 기사는 한 번만 세고, 다른 조직의 기사는 세지 않는다."""
    own = make_organization(db)
    first = make_user(db, own)
    second = make_user(db, own)
    shared = make_article(db)
    link(db, first, shared)
    link(db, second, shared)
    link(db, second, make_article(db))
    link(db, make_user(db, make_organization(db)), make_article(db))

    assert tools._count_articles(db, own.id, "all") == 2


def test_count_articles_period_and_category(db):
    """기간은 작성일(없으면 업로드 시각) 기준으로 거르고, 분야로도 거른다."""
    now = datetime.now(KST)
    user = make_user(db, make_organization(db))
    link(db, user, make_article(db, category="경제", published_at=now))
    link(db, user, make_article(db))
    link(db, user, make_article(db, category="IT", published_at=now - timedelta(days=800)))
    organization_id = user.organization_id

    assert tools._count_articles(db, organization_id, "all") == 3
    assert tools._count_articles(db, organization_id, "today") == 2
    assert tools._count_articles(db, organization_id, "yesterday") == 0
    assert tools._count_articles(db, organization_id, "this_year") == 2
    assert tools._count_articles(db, organization_id, "all", "경제") == 1


def test_count_articles_by_category_uncategorized(db):
    """분야가 없는 기사는 미분류로 세고, 많은 순서로 반환한다."""
    user = make_user(db, make_organization(db))
    for category in ["경제", "경제", "IT", None]:
        link(db, user, make_article(db, category=category))

    result = tools._count_articles_by_category(db, user.organization_id, "all")

    assert result == [("경제", 2), ("IT", 1), ("미분류", 1)]


def test_list_recent_articles_order_and_limit(db):
    """최근 기사를 최신순으로 최대 5개 반환하고, 여러 명이 가진 기사도 한 번만 넣는다."""
    now = datetime.now(KST)
    organization = make_organization(db)
    user = make_user(db, organization)
    articles = []
    for days in range(7):
        article = make_article(db, title=f"{days}일 전 기사", published_at=now - timedelta(days=days))
        link(db, user, article)
        articles.append(article)
    link(db, make_user(db, organization), articles[0])

    rows = tools._list_recent_articles(db, organization.id, "all")

    assert [row.title for row in rows] == [f"{days}일 전 기사" for days in range(5)]


def test_count_articles_by_author_and_media_escape(db):
    """기자·언론사 이름이 들어간 기사를 세고, %와 _는 글자 그대로 찾는다."""
    user = make_user(db, make_organization(db))
    for author, media in [("김바다, 이하늘", "새봄신문"), ("이하늘", "한빛일보"),
                          ("100%기자", "새봄_신문"), ("박구름", "새봄X신문")]:
        link(db, user, make_article(db, author=author, media=media))
    organization_id = user.organization_id

    assert tools._count_articles_by_author(db, organization_id, "all", "이하늘") == 2
    assert tools._count_articles_by_author(db, organization_id, "all", "%") == 1
    assert tools._count_articles_by_media(db, organization_id, "all", "새봄") == 3
    assert tools._count_articles_by_media(db, organization_id, "all", "새봄_신문") == 1


def test_list_templates_guidelines_and_count_members(db):
    """템플릿·지침 제목과 구성원 수는 자기 조직 것만 반환한다."""
    own = make_organization(db)
    other = make_organization(db)
    make_user(db, own)
    make_user(db, own)
    make_user(db, other)
    make_template(db, own)
    make_template(db, other)
    save(db, Guideline(organization_id=own.id, title="표기 원칙", content="숫자 표기"))
    save(db, Guideline(organization_id=other.id, title="다른 조직 지침", content="내용"))

    assert tools._list_templates(db, own.id) == ["보도자료"]
    assert tools._list_guidelines(db, own.id) == ["표기 원칙"]
    assert tools._count_members(db, own.id) == 2


# 관리자 기능 (repositories/admin_repository.py)
# 함수가 db를 인자로 받으므로 db를 그대로 넘긴다. commit은 서비스가 하므로 flush된 결과로 확인한다.


def test_admin_get_organization_and_members(db):
    """조직을 id로 찾고, 구성원은 자기 조직만 조회하며 다른 조직 구성원은 None을 반환한다."""
    own = make_organization(db)
    first = make_user(db, own)
    second = make_user(db, own)
    outsider = make_user(db, make_organization(db))

    assert admin_repository.get_organization(db, own.id).code == own.code
    members = admin_repository.get_org_members(db, own.id)
    assert sorted(member.id for member in members) == sorted([first.id, second.id])
    assert admin_repository.get_org_member(db, own.id, first.id).id == first.id
    assert admin_repository.get_org_member(db, own.id, outsider.id) is None


def test_admin_get_template_guideline_other_organization(db):
    """다른 조직의 템플릿·지침은 조회되지 않고, 지침 목록은 자기 조직 것만 반환한다."""
    own = make_organization(db)
    other = make_organization(db)
    own_guideline = save(db, Guideline(organization_id=own.id, title="표기 원칙", content="숫자 표기"))
    other_guideline = save(db, Guideline(organization_id=other.id, title="다른 조직 지침", content="내용"))
    other_template = make_template(db, other)

    assert admin_repository.get_org_template(db, own.id, other_template.id) is None
    found = admin_repository.get_org_template(db, other.id, other_template.id)
    assert found.id == other_template.id
    assert admin_repository.get_org_guideline(db, own.id, other_guideline.id) is None
    guidelines = admin_repository.get_org_guidelines(db, own.id)
    assert [guideline.id for guideline in guidelines] == [own_guideline.id]


def test_admin_add_and_update_template_guideline(db):
    """템플릿·지침을 추가하면 id가 생기고, 제목과 내용을 수정할 수 있다."""
    organization = make_organization(db)
    template = admin_repository.add_template(
        db, Template(organization_id=organization.id, title="보도자료", content="제목과 본문"))
    guideline = admin_repository.add_guideline(
        db, Guideline(organization_id=organization.id, title="표기 원칙", content="숫자 표기"))
    assert template.id is not None
    assert guideline.id is not None

    admin_repository.update_template(db, template, "인터뷰", "질문과 답변")
    admin_repository.update_guideline(db, guideline, "인용 원칙", "실명으로 인용")
    db.expunge_all()   # 세션 캐시가 아니라 DB에서 다시 읽게 한다

    found_template = db.get(Template, template.id)
    found_guideline = db.get(Guideline, guideline.id)
    assert (found_template.title, found_template.content) == ("인터뷰", "질문과 답변")
    assert (found_guideline.title, found_guideline.content) == ("인용 원칙", "실명으로 인용")


def test_admin_update_member(db):
    """구성원의 닉네임과 role을 따로 바꿀 수 있고, 넘기지 않은 값은 그대로 둔다."""
    member = make_user(db, make_organization(db))

    admin_repository.update_member(db, member, nickname="이하늘")
    admin_repository.update_member(db, member, role="admin")
    db.expunge_all()

    found = db.get(User, member.id)
    assert (found.nickname, found.role) == ("이하늘", "admin")


def test_admin_delete_record_template_guideline(db):
    """템플릿과 지침을 삭제한다."""
    organization = make_organization(db)
    template = make_template(db, organization)
    guideline = save(db, Guideline(organization_id=organization.id, title="표기 원칙", content="숫자 표기"))

    admin_repository.delete_record(db, template)
    admin_repository.delete_record(db, guideline)

    assert count(db, Template, Template.id == template.id) == 0
    assert count(db, Guideline, Guideline.id == guideline.id) == 0


def test_admin_delete_record_user_removes_private_articles(db):
    """구성원을 지우면 그의 대화·비공개 기사·연결·토큰이 지워지고, 공개 기사와 동료의 연결은 남는다."""
    organization = make_organization(db)
    member = make_user(db, organization)
    colleague = make_user(db, organization)
    private = make_article(db, visibility="private")
    public = make_article(db, visibility="public")
    link(db, member, private)
    link(db, member, public)
    link(db, colleague, public)
    save(db, make_chunk(private, 0, "비공개 기사 조각"))
    make_conversation(db, member, public)
    token = unique("token")
    expired_at = datetime.now(timezone.utc) + timedelta(days=7)
    refresh_token_repository.create(db, member.id, token, expired_at)

    admin_repository.delete_record(db, member)

    assert count(db, User, User.id == member.id) == 0
    assert count(db, Conversation, Conversation.user_id == member.id) == 0
    assert count(db, Article, Article.id == private.id) == 0
    assert count(db, ArticleChunk, ArticleChunk.article_id == private.id) == 0
    assert count(db, UserArticle, UserArticle.user_id == member.id) == 0
    assert refresh_token_repository.get_by_token(db, token) is None
    assert count(db, Article, Article.id == public.id) == 1
    assert count(db, UserArticle, UserArticle.user_id == colleague.id) == 1


def test_admin_delete_record_user_with_messages(db):
    """메시지가 있는 대화를 가진 구성원도 대화·메시지와 함께 삭제된다."""
    member = make_user(db, make_organization(db))
    article = make_article(db, visibility="public")
    link(db, member, article)
    conversation = make_conversation(db, member, article)
    save(db, Message(conversation_id=conversation.id, role="user", content="질문"))

    admin_repository.delete_record(db, member)

    assert count(db, User, User.id == member.id) == 0
    assert count(db, Message, Message.conversation_id == conversation.id) == 0
