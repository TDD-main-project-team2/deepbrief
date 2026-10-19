import os
from unittest.mock import MagicMock, patch

import pytest

from backend.services.ai import embedding_service as service


@pytest.fixture(autouse=True)
def clear_model_cache():
    """테스트 간 모델 캐시가 영향을 주지 않도록 초기화한다."""
    service._get_embedding_model.cache_clear()
    yield
    service._get_embedding_model.cache_clear()


def test_embed_documents_empty():
    """빈 문서 목록은 빈 결과를 반환하고 모델을 로드하지 않는다."""
    with patch.object(service, "_get_embedding_model") as get_model:
        result = service.embed_documents([])

    assert result == []
    get_model.assert_not_called()


def test_embed_documents():
    """문서 목록을 임베딩하고 정규화 옵션을 전달한다."""
    fake_model = MagicMock()
    fake_model.encode.return_value.tolist.return_value = [
        [0.6, 0.8],
        [1.0, 0.0],
    ]

    with patch.object(
        service, "_get_embedding_model", return_value=fake_model
    ):
        result = service.embed_documents(["문서 1", "문서 2"])

    assert result == [[0.6, 0.8], [1.0, 0.0]]
    fake_model.encode.assert_called_once_with(
        ["문서 1", "문서 2"],
        normalize_embeddings=True,
        show_progress_bar=True,
    )


def test_embed_query():
    """질문 하나를 임베딩하고 정규화 옵션을 전달한다."""
    fake_model = MagicMock()
    fake_model.encode.return_value.tolist.return_value = [0.6, 0.8]

    with patch.object(
        service, "_get_embedding_model", return_value=fake_model
    ):
        result = service.embed_query("검색 질문")

    assert result == [0.6, 0.8]
    fake_model.encode.assert_called_once_with(
        "검색 질문",
        normalize_embeddings=True,
        show_progress_bar=True,
    )


def test_get_embedding_model_caches_instance():
    """모델은 최초 로드 후 동일한 인스턴스를 재사용한다."""
    with patch.object(
        service, "SentenceTransformer"
    ) as model_class:
        first = service._get_embedding_model()
        second = service._get_embedding_model()

    assert first is second
    model_class.assert_called_once_with(service.MODEL_NAME)


def test_model_name():
    """사용하는 임베딩 모델 이름을 확인한다."""
    assert service.MODEL_NAME == "BAAI/bge-m3"


@pytest.mark.skipif(
    os.getenv("RUN_EMBEDDING_INTEGRATION") != "1",
    reason="실제 모델 테스트는 RUN_EMBEDDING_INTEGRATION=1일 때만 실행",
)
def test_real_embedding_model():
    """실제 BGE-M3 모델로 문서와 질문 임베딩을 생성한다."""
    document_vectors = service.embed_documents(
        ["DeepBrief는 기사 분석을 지원한다.", "기사는 검색을 위해 임베딩된다."]
    )
    query_vector = service.embed_query("기사 분석 기능은 무엇인가?")

    assert len(document_vectors) == 2
    assert all(len(vector) == 1024 for vector in document_vectors)
    assert len(query_vector) == 1024

    for vector in [*document_vectors, query_vector]:
        assert all(isinstance(value, float) for value in vector)
        norm = sum(value * value for value in vector) ** 0.5
        assert norm == pytest.approx(1.0, abs=1e-4)
