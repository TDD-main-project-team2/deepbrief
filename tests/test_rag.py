from types import SimpleNamespace

import pytest

from backend.services.rag import rag_service
from backend.services.ai import model_service

ARTICLE_ID = 174  # 전세 사기 관련 기사(홍길동 사용자)

# 1. 문서 검색·컨텍스트(9개 테스트 함수)
# 저장된 청크 조회, 질문에 맞는 근거 검색, 문서 범위·개수 제한,
# 검색한 청크를 답변용 문자열로 결합하는 기능을 확인한다.

def test_retrieve_article_chunks():
    """청크가 존재하고 문서 ID와 0부터 이어지는 인덱스 순서가 올바른지 확인한다."""

    chunks = rag_service.retrieve_article_chunks(ARTICLE_ID)

    assert chunks
    assert all(chunk.article_id == ARTICLE_ID for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_retrieve_similar_article_chunks():
    """질문으로 검색한 상위 청크에 미리 정한 정답 근거가 포함되는지 확인한다."""
    
    question = "전세사기 피해자를 위한 임차보증금 최소보장제는 언제 시행되나요?"
    expected_text = "11월 13일부터 시행한다."
    top_k = 5

    chunks = rag_service.retrieve_similar_article_chunks(question, ARTICLE_ID, top_k)

    assert chunks
    assert len(chunks) <= top_k
    assert all(chunk.article_id == ARTICLE_ID for chunk in chunks)
    assert any(expected_text in chunk.content for chunk in chunks)


def test_retrieve_paraphrased_question():
    """표현을 바꾼 같은 의미의 질문에도 정답 근거를 찾는지 확인한다."""
    
    question = "전세사기로 잃은 보증금을 최소한으로 보장해 주는 제도는 언제부터 시작하나요?"
    expected_text = "11월 13일부터 시행한다."
    top_k = 5

    chunks = rag_service.retrieve_similar_article_chunks(question, ARTICLE_ID, top_k)

    assert chunks
    assert len(chunks) <= top_k
    assert all(chunk.article_id == ARTICLE_ID for chunk in chunks)
    assert any(expected_text in chunk.content for chunk in chunks)


def test_retrieve_multiple_evidence_chunks():
    """여러 청크의 정보가 필요한 질문에 필요한 근거들이 함께 검색되는지 확인한다."""

    question = "임차보증금 최소보장제는 언제 시행되며, LH는 신청 후 며칠 이내에 지급 여부와 지급액을 결정해?"
    expected_start = "최소보장제가 시행되는 11월 13일"
    expected_deadline = "신청일로부터 90일 이내에 지급 여부와 지급액을 결정해 통지해야 한다."
    top_k = 5

    chunks = rag_service.retrieve_similar_article_chunks(question, ARTICLE_ID, top_k)

    assert chunks
    assert len(chunks) <= top_k
    assert all(chunk.article_id == ARTICLE_ID for chunk in chunks)
    assert any(
        expected_start in first.content
        and expected_deadline in second.content
        and first.chunk_index != second.chunk_index
        for first in chunks
        for second in chunks
    )


def test_retrieve_article_scope():
    """비슷한 내용의 다른 문서가 있어도 지정한 문서의 청크만 반환되는지 확인한다."""

    question = "전세사기 피해자 지원 제도는 무엇인가요?"

    chunks = rag_service.retrieve_similar_article_chunks(question, ARTICLE_ID, top_k=5)

    assert chunks
    assert all(chunk.article_id == ARTICLE_ID for chunk in chunks)


def test_retrieve_top_k():
    """검색 결과 개수가 top_k와 저장된 청크 수 중 작은 값과 일치하는지 확인한다."""

    question = "임차보증금 최소보장제는 언제 시행되나요?"
    stored_chunks = rag_service.retrieve_article_chunks(ARTICLE_ID)

    assert stored_chunks
    for top_k in (1, 3, 5, len(stored_chunks) + 1):
        chunks = rag_service.retrieve_similar_article_chunks(question, ARTICLE_ID, top_k)

        assert len(chunks) == min(top_k, len(stored_chunks))


def test_retrieve_article_without_chunks():
    """존재하지 않는 문서 ID로 조회·검색하면 빈 목록이 반환되는지 확인한다."""

    article_id = -1  # 테스트 DB에 존재하지 않는 문서 ID
    question = "임차보증금 최소보장제는 언제 시행되나요?"

    assert rag_service.retrieve_article_chunks(article_id) == []
    assert rag_service.retrieve_similar_article_chunks(question, article_id) == []


def test_build_context():
    """검색 청크의 본문이 입력 순서대로 '\\n\\n'으로 연결되는지 확인한다."""

    chunks = [
        SimpleNamespace(content="최소보장제는 11월 13일부터 시행한다."),
        SimpleNamespace(content="LH는 신청일로부터 90일 이내에 지급 여부를 결정한다."),
    ]

    context = rag_service.build_context(chunks)

    assert context == (
        "최소보장제는 11월 13일부터 시행한다.\n\n"
        "LH는 신청일로부터 90일 이내에 지급 여부를 결정한다."
    )


def test_build_context_empty():
    """빈 청크 목록을 전달하면 빈 문자열이 반환되는지 확인한다."""

    assert rag_service.build_context([]) == ""


# 2. 검색 범위 판단(3개 테스트 함수)
# 질문과 현재 문서의 근거를 보고 current_article, company_data, web 중
# 알맞은 경로를 선택하는지 확인한다. 현재 자동 판단에는 organization이 없다.

def test_classify_current_article():
    """현재 문서의 근거로 답할 수 있는 질문을 current_article로 판단하는지 확인한다."""

    question = "임차보증금 최소보장제는 언제 시행되나요?"
    chunks = rag_service.retrieve_similar_article_chunks(question, ARTICLE_ID)
    context = rag_service.build_context(chunks)

    assert "11월 13일부터 시행한다." in context
    assert model_service.classify_retrieval_scope(question, context) == "current_article"


def test_classify_company_data():
    """사내 기사 수·목록 등 DB 조회가 필요한 질문을 company_data로 판단하는지 확인한다."""

    question = "우리 회사의 이번 달 기사 수는 몇 건인가요?"
    chunks = rag_service.retrieve_similar_article_chunks(question, ARTICLE_ID)
    context = rag_service.build_context(chunks)

    assert context
    assert model_service.classify_retrieval_scope(question, context) == "company_data"


def test_classify_web():
    """사내 조회 질문이 아니고 현재 문서로 답할 수 없으면 web으로 판단하는지 확인한다."""
    
    question = "식물의 광합성은 어떤 원리로 이루어지나요?"
    chunks = rag_service.retrieve_similar_article_chunks(question, ARTICLE_ID)
    context = rag_service.build_context(chunks)

    assert context
    assert model_service.classify_retrieval_scope(question, context) == "web"


# 3. 추가 검색·조회(7개 테스트 함수)
# 조직 문서 검색의 범위, 웹 결과 가공, 사내 조회 도구 선택과 실패 처리를 확인한다.
# 조직 검색은 자동 분류와 별도로 직접 호출해 검증한다.
# 웹 처리 로직은 고정한 응답으로 검증하고 실제 API 연결 확인은 따로 수행한다.

@pytest.mark.skip(reason="미구현")
def test_retrieve_org_chunks():
    """같은 조직의 다른 문서에서 검색하고 현재 문서와 다른 조직 문서는 제외하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_retrieve_org_chunks_by_embedding():
    """질문 벡터를 직접 전달해 검색할 때 정답 근거, 조직 범위, top_k 제한을 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_retrieve_org_chunks_without_organization():
    """문서에 연결된 조직이 없으면 조직 검색에서 ValueError가 발생하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_search_web():
    """유효한 웹 검색 결과의 제목과 내용을 답변용 컨텍스트로 구성하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_search_web_failure():
    """웹 요청 오류·시간 초과·잘못된 JSON 응답 시 빈 컨텍스트를 반환하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_query_company_data():
    """질문에 맞는 조회 도구·인자를 사용하고 해당 조직의 DB 데이터만 조회하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_query_company_data_failure():
    """연결된 조직이 없거나 DB 조회가 실패하면 빈 문자열을 반환하는지 확인한다."""
    pass


# 4. 에이전트 전체 흐름(5개 테스트 함수)
# 실제 선택 경로, 호출된 검색·조회 도구, 최종 컨텍스트와 답변을 함께 확인한다.
# 답변이 맞더라도 실제 검색 근거로 뒷받침되지 않으면 성공으로 판단하지 않는다.

@pytest.mark.skip(reason="미구현")
def test_answer_from_current_article():
    """현재 문서 경로를 선택하고 검색한 청크에 근거해 정확히 답하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_answer_from_company_data():
    """사내 조회 경로를 선택하고 실제 조회 결과의 수치·내용에 맞게 답하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_answer_from_web():
    """웹 경로를 선택하고 실제 호출된 검색 도구의 반환 내용에 근거해 답하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_answer_with_empty_context():
    """최종 컨텍스트가 비어 있으면 NOT_FOUND_MESSAGE를 반환하는지 확인한다."""
    pass


@pytest.mark.skip(reason="미구현")
def test_answer_without_evidence():
    """컨텍스트가 있어도 정답 근거가 없으면 내용을 지어내지 않는지 확인한다."""
    pass
