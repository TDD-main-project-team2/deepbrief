from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

import pytest, asyncio
from fastapi import HTTPException

from backend.services.resources import organization_service, article_service, conversation_service
from backend.app.dependencies import ensure_organization_member


def test_get_organization_by_user_id_success(monkeypatch):
    db = object()
    organization = SimpleNamespace(id=10)

    find_org = Mock(return_value=organization)
    check_member = Mock()

    monkeypatch.setattr(
        organization_service.organization_repository,
        "find_organization_by_user_id",
        find_org,
    )
    monkeypatch.setattr(
        organization_service,
        "ensure_organization_member",
        check_member,
    )

    result = organization_service.get_organization_by_user_id(3, db)

    assert result is organization
    find_org.assert_called_once_with(3, db)
    check_member.assert_called_once_with(10, 3, db)


def test_get_organization_by_user_id_not_found(monkeypatch):
    db = object()

    monkeypatch.setattr(
        organization_service.organization_repository,
        "find_organization_by_user_id",
        Mock(return_value=None),
    )
    check_member = Mock()
    monkeypatch.setattr(
        organization_service,
        "ensure_organization_member",
        check_member,
    )

    with pytest.raises(HTTPException) as exc_info:
        organization_service.get_organization_by_user_id(3, db)

    assert exc_info.value.status_code == 404
    check_member.assert_not_called()


def test_get_organization_article_template(monkeypatch):
    db = object()
    organization = SimpleNamespace(id=10)
    template = SimpleNamespace(id=20)

    monkeypatch.setattr(
        organization_service,
        "get_organization_by_user_id",
        Mock(return_value=organization),
    )
    find_template = Mock(return_value=template)
    monkeypatch.setattr(
        organization_service.organization_repository,
        "find_article_template_by_id",
        find_template,
    )

    result = organization_service.get_organization_article_template_for_user(
        3, 20, db
    )

    assert result is template
    find_template.assert_called_once_with(10, 20, db)


def test_get_organization_evaluation_guideline(monkeypatch):
    db = object()
    organization = SimpleNamespace(id=10)
    guideline = SimpleNamespace(id=30)

    monkeypatch.setattr(
        organization_service,
        "get_organization_by_user_id",
        Mock(return_value=organization),
    )
    find_guideline = Mock(return_value=guideline)
    monkeypatch.setattr(
        organization_service.organization_repository,
        "find_org_guideline_by_id",
        find_guideline,
    )

    result = (
        organization_service
        .get_organization_evaluation_guideline_for_user(3, 30, db)
    )

    assert result is guideline
    find_guideline.assert_called_once_with(10, 30, db)


def test_get_all_organization_article_templates(monkeypatch):
    db = object()
    organization = SimpleNamespace(id=10)
    templates = [
        SimpleNamespace(id=20),
        SimpleNamespace(id=21),
    ]

    monkeypatch.setattr(
        organization_service,
        "get_organization_by_user_id",
        Mock(return_value=organization),
    )
    find_templates = Mock(return_value=templates)
    monkeypatch.setattr(
        organization_service.organization_repository,
        "find_all_article_templates",
        find_templates,
    )

    result = organization_service.get_all_organization_article_templates(
        3, db
    )

    assert result == templates
    find_templates.assert_called_once_with(10, db)

def test_ensure_organization_member_success():
    db = Mock()
    db.get.return_value = SimpleNamespace(
        id=3,
        organization_id=10,
    )

    ensure_organization_member(10, 3, db)

    db.get.assert_called_once()


def test_ensure_organization_member_wrong_organization():
    db = Mock()
    db.get.return_value = SimpleNamespace(
        id=3,
        organization_id=20,
    )

    with pytest.raises(HTTPException) as exc_info:
        ensure_organization_member(10, 3, db)

    assert exc_info.value.status_code == 404


def test_ensure_organization_member_user_not_found():
    db = Mock()
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        ensure_organization_member(10, 3, db)

    assert exc_info.value.status_code == 404


def test_delete_article_removes_user_article_link(monkeypatch):
    article = SimpleNamespace(id=10)

    find_article = Mock(return_value=article)
    delete_link = Mock(return_value=True)

    monkeypatch.setattr(
        article_service.article_repository,
        "find_article_by_id",
        find_article,
    )
    monkeypatch.setattr(
        article_service.article_repository,
        "delete_article",
        delete_link,
    )

    article_service.delete_article(10, 3)

    find_article.assert_called_once_with(10)
    delete_link.assert_called_once_with(10, 3)


def test_delete_article_without_user_link_returns_404(monkeypatch):
    article = SimpleNamespace(id=10)

    monkeypatch.setattr(
        article_service.article_repository,
        "find_article_by_id",
        Mock(return_value=article),
    )
    monkeypatch.setattr(
        article_service.article_repository,
        "delete_article",
        Mock(return_value=False),
    )

    with pytest.raises(HTTPException) as exc_info:
        article_service.delete_article(10, 3)

    assert exc_info.value.status_code == 404

def test_create_conversation_registers_article_for_user(monkeypatch):
    uploaded_file = SimpleNamespace(
        read=AsyncMock(return_value=b"test article content"),
        filename="sample.txt",
    )
    article = SimpleNamespace(id=123)
    created_conversation = SimpleNamespace(id=456)
    db = object()

    process_article = Mock(return_value=article)
    categorize_article = Mock()
    add_article_to_user = Mock()
    create_conversation = Mock(return_value=created_conversation)

    monkeypatch.setattr(
        conversation_service.article_processing_service,
        "process_article",
        process_article,
    )
    monkeypatch.setattr(
        conversation_service.article_service,
        "categorize_article",
        categorize_article,
    )
    monkeypatch.setattr(
        conversation_service.article_repository,
        "add_article_to_user",
        add_article_to_user,
    )
    monkeypatch.setattr(
        conversation_service.conversation_repository,
        "create_conversation",
        create_conversation,
    )

    result = asyncio.run(
        conversation_service.create_conversation(
            uploaded_file,
            "테스트 대화",
            7,
            db,
        )
    )

    assert result is created_conversation
    process_article.assert_called_once_with(
        b"test article content",
        "sample.txt",
        db,
        reprocess=False,
    )
    categorize_article.assert_called_once_with(123)
    add_article_to_user.assert_called_once_with(7, 123)
    create_conversation.assert_called_once_with(
        "테스트 대화",
        7,
        123,
    )