import asyncio

import pytest

from backend.services.agent import nodes, tools
from backend.services.ai import model_service



def test_retrieve_article_context(monkeypatch):
    """현재 기사에서 관련 청크를 검색하고 문맥을 구성한다."""
    calls = {}

    def fake_retrieve(question, article_id):
        calls["retrieve"] = (question, article_id)
        return ["chunk1", "chunk2"]

    def fake_build_context(chunks):
        calls["chunks"] = chunks
        return "현재 기사 문맥"

    monkeypatch.setattr(
        nodes.rag_service,
        "retrieve_similar_article_chunks",
        fake_retrieve,
    )
    monkeypatch.setattr(
        nodes.rag_service,
        "build_context",
        fake_build_context,
    )

    result = nodes.retrieve_article_context(
        {"question": "기사 내용이 뭐야?", "article_id": 1}
    )

    assert calls["retrieve"] == ("기사 내용이 뭐야?", 1)
    assert calls["chunks"] == ["chunk1", "chunk2"]
    assert result == {"context": "현재 기사 문맥"}


def test_decide_retrieval_scope(monkeypatch):
    """LLM이 판단한 검색 범위를 상태에 반환한다."""
    calls = {}

    def fake_classify(question, context):
        calls["args"] = (question, context)
        return "web"

    monkeypatch.setattr(
        nodes.model_service,
        "classify_retrieval_scope",
        fake_classify,
    )

    result = nodes.decide_retrieval_scope(
        {
            "question": "관련 최신 정보를 찾아줘",
            "context": "현재 기사 문맥",
        }
    )

    assert calls["args"] == (
        "관련 최신 정보를 찾아줘",
        "현재 기사 문맥",
    )
    assert result == {"retrieval_scope": "web"}


def test_retrieve_additional_context_current_article():
    """현재 기사 범위에서는 추가 검색을 하지 않는다."""
    result = nodes.retrieve_additional_context(
        {"retrieval_scope": "current_article"}
    )

    assert result == {}


def test_retrieve_additional_context_organization(monkeypatch):
    """조직 범위에서는 사내 기사 RAG 검색을 실행한다."""
    calls = {}

    def fake_retrieve(question, article_id):
        calls["args"] = (question, article_id)
        return ["organization chunk"]

    def fake_build_context(chunks):
        calls["chunks"] = chunks
        return "사내 기사 문맥"

    monkeypatch.setattr(
        nodes.rag_service,
        "retrieve_org_chunks",
        fake_retrieve,
    )
    monkeypatch.setattr(
        nodes.rag_service,
        "build_context",
        fake_build_context,
    )

    result = nodes.retrieve_additional_context(
        {
            "question": "회사 관련 기사 찾아줘",
            "article_id": 10,
            "retrieval_scope": "organization",
        }
    )

    assert calls["args"] == ("회사 관련 기사 찾아줘", 10)
    assert calls["chunks"] == ["organization chunk"]
    assert result == {"context": "사내 기사 문맥"}


def test_retrieve_additional_context_web(monkeypatch):
    """웹 범위에서는 웹 검색 도구를 호출한다."""
    calls = {}

    def fake_search_web(question):
        calls["question"] = question
        return "웹 검색 결과"

    monkeypatch.setattr(nodes.tools, "search_web", fake_search_web)

    result = nodes.retrieve_additional_context(
        {
            "question": "최신 뉴스 찾아줘",
            "article_id": 1,
            "retrieval_scope": "web",
        }
    )

    assert calls["question"] == "최신 뉴스 찾아줘"
    assert result == {"context": "웹 검색 결과"}


def test_retrieve_additional_context_company_data(monkeypatch):
    """사내 데이터 범위에서는 회사 데이터 조회 도구를 호출한다."""
    calls = {}

    def fake_query_company_data(question, article_id):
        calls["args"] = (question, article_id)
        return "사내 데이터 조회 결과"

    monkeypatch.setattr(
        nodes.tools,
        "query_company_data",
        fake_query_company_data,
    )

    result = nodes.retrieve_additional_context(
        {
            "question": "회사 기사 몇 개야?",
            "article_id": 7,
            "retrieval_scope": "company_data",
        }
    )

    assert calls["args"] == ("회사 기사 몇 개야?", 7)
    assert result == {"context": "사내 데이터 조회 결과"}


def test_retrieve_additional_context_unknown_scope():
    """지원하지 않는 검색 범위는 오류를 발생시킨다."""
    with pytest.raises(ValueError, match="Unknown retrieval scope"):
        nodes.retrieve_additional_context(
            {"retrieval_scope": "unknown"}
        )


def test_answer_question_without_context(monkeypatch):
    """문맥이 없으면 LLM 답변 생성 없이 미검색 메시지를 반환한다."""
    def unexpected_generate_answer(*args, **kwargs):
        pytest.fail("문맥이 없을 때 답변 생성 함수가 호출되면 안 됩니다.")

    monkeypatch.setattr(
        nodes.model_service,
        "generate_answer",
        unexpected_generate_answer,
    )

    result = nodes.answer_question(
        {"context": "   ", "question": "질문"}
    )

    assert result == {
        "answer": nodes.model_service.NOT_FOUND_MESSAGE
    }


def test_answer_question_with_context(monkeypatch):
    """문맥이 있으면 LLM 답변 생성 결과를 반환한다."""
    calls = {}

    def fake_generate_answer(context, question):
        calls["args"] = (context, question)
        return "생성된 답변"

    monkeypatch.setattr(
        nodes.model_service,
        "generate_answer",
        fake_generate_answer,
    )

    result = nodes.answer_question(
        {
            "context": "검증용 문맥",
            "question": "무슨 내용이야?",
        }
    )

    assert calls["args"] == ("검증용 문맥", "무슨 내용이야?")
    assert result == {"answer": "생성된 답변"}


def test_agent_graph_end_to_end_with_mocks(monkeypatch):
    """검색부터 최종 답변까지 그래프가 연결되는지 검증한다."""
    from backend.services.agent.graph import build_graph

    monkeypatch.setattr(
        nodes.rag_service,
        "retrieve_similar_article_chunks",
        lambda question, article_id: ["테스트 청크"],
    )
    monkeypatch.setattr(
        nodes.rag_service,
        "build_context",
        lambda chunks: "테스트 문맥",
    )
    monkeypatch.setattr(
        nodes.model_service,
        "classify_retrieval_scope",
        lambda question, context: "current_article",
    )
    monkeypatch.setattr(
        nodes.model_service,
        "generate_answer",
        lambda context, question: "테스트 답변",
    )

    graph = build_graph()

    result = asyncio.run(
        graph.ainvoke(
            {
                "question": "테스트 질문",
                "article_id": 1,
                "conversation_history": [],
                "context": "",
                "retrieval_scope": "",
                "answer": "",
            }
        )
    )

    assert result["context"] == "테스트 문맥"
    assert result["retrieval_scope"] == "current_article"
    assert result["answer"] == "테스트 답변"


def test_select_company_data_tool_parses_tool_call(monkeypatch):
    """모델의 도구 호출 출력을 올바르게 파싱한다."""
    calls = {}

    def fake_generate(messages, adapter, feature, tools=None):
        calls["messages"] = messages
        calls["adapter"] = adapter
        calls["feature"] = feature
        calls["tools"] = tools
        return (
            '<tool_call>{"name": "count_articles", '
            '"arguments": {"period": "all", "category": "정치"}}'
            '</tool_call>'
        )

    monkeypatch.setattr(model_service, "_generate", fake_generate)

    result = model_service.select_company_data_tool(
        "우리 회사 정치 기사는 몇 개야?"
    )

    assert result == {
        "name": "count_articles",
        "arguments": {"period": "all", "category": "정치"},
    }
    assert calls["adapter"] is None
    assert calls["feature"] == "company_data_tool"
    assert calls["tools"] == model_service.COMPANY_DATA_TOOLS
    assert calls["messages"][-1]["content"] == "우리 회사 정치 기사는 몇 개야?"


def test_select_company_data_tool_without_tool_call(monkeypatch):
    """모델이 도구를 선택하지 않으면 None을 반환한다."""
    monkeypatch.setattr(
        model_service,
        "_generate",
        lambda *args, **kwargs: "없음",
    )

    result = model_service.select_company_data_tool("전기버스와 수소버스의 차이는?")
    assert result is None


def test_classify_retrieval_scope_company_data(monkeypatch):
    """사내 데이터 조회 도구가 선택되고 회사 관련 표현이 있으면 company_data."""
    monkeypatch.setattr(
        model_service,
        "select_company_data_tool",
        lambda question: {
            "name": "count_articles",
            "arguments": {"period": "all"},
        },
    )

    def unexpected_decide(*args, **kwargs):
        pytest.fail("company_data 결정 후에는 기사 QA를 호출하면 안 됩니다.")

    monkeypatch.setattr(
        model_service,
        "decide_answer_source",
        unexpected_decide,
    )

    result = model_service.classify_retrieval_scope(
        "우리 회사 기사 몇 개야?",
        "현재 기사 문맥",
    )

    assert result == "company_data"


def test_classify_retrieval_scope_current_article(monkeypatch):
    """현재 기사에서 근거가 있는 답을 얻으면 current_article."""
    monkeypatch.setattr(
        model_service,
        "select_company_data_tool",
        lambda question: None,
    )
    monkeypatch.setattr(
        model_service,
        "decide_answer_source",
        lambda context, question: {
            "source": "current_article",
            "answer": "서울시는 오늘 사업 계획을 발표했다.",
        },
    )

    result = model_service.classify_retrieval_scope(
        "서울시는 무엇을 발표했어?",
        "서울시는 오늘 사업 계획을 발표했다.",
    )

    assert result == "current_article"


def test_classify_retrieval_scope_rejects_echoed_answer(monkeypatch):
    """질문을 되풀이한 답은 인정하지 않고 web으로 분류한다."""
    monkeypatch.setattr(
        model_service,
        "select_company_data_tool",
        lambda question: None,
    )
    monkeypatch.setattr(
        model_service,
        "decide_answer_source",
        lambda context, question: {
            "source": "current_article",
            "answer": "전기버스",
        },
    )

    result = model_service.classify_retrieval_scope(
        "전기버스와 수소버스의 차이는?",
        "전기버스와 수소버스의 특징을 설명한 기사",
    )

    assert result == "web"


def test_classify_retrieval_scope_empty_context(monkeypatch):
    """문맥이 비어 있으면 기사 QA를 실행하지 않고 web으로 분류한다."""
    monkeypatch.setattr(
        model_service,
        "select_company_data_tool",
        lambda question: None,
    )

    def unexpected_decide(*args, **kwargs):
        pytest.fail("빈 문맥에서는 기사 QA를 호출하면 안 됩니다.")

    monkeypatch.setattr(
        model_service,
        "decide_answer_source",
        unexpected_decide,
    )

    result = model_service.classify_retrieval_scope(
        "최근 상황을 알려줘",
        "   ",
    )

    assert result == "web"


def test_parse_tool_call_json_string_arguments():
    """도구 인자가 JSON 문자열로 반환돼도 정상 파싱한다."""
    raw = (
        '<tool_call>{"name": "count_articles", '
        '"arguments": "{\\"period\\": \\"all\\"}"}</tool_call>'
    )

    result = model_service._parse_tool_call(raw)

    assert result == {
        "name": "count_articles",
        "arguments": {"period": "all"},
    }


def test_parse_tool_call_invalid_json():
    """잘못된 JSON은 도구 호출로 인정하지 않는다."""
    result = model_service._parse_tool_call(
        '<tool_call>{"name": "count_articles",}</tool_call>'
    )

    assert result is None


def test_classify_retrieval_scope_without_company_cue(monkeypatch):
    """사내 도구가 선택돼도 질문에 회사 관련 표현이 없으면 기사 답변을 판단한다."""
    monkeypatch.setattr(
        model_service,
        "select_company_data_tool",
        lambda question: {
            "name": "count_articles",
            "arguments": {"period": "all"},
        },
    )
    monkeypatch.setattr(
        model_service,
        "decide_answer_source",
        lambda context, question: {
            "source": "current_article",
            "answer": "서울시는 사업 계획을 발표했다.",
        },
    )

    result = model_service.classify_retrieval_scope(
        "서울시는 무엇을 발표했어?",
        "서울시는 사업 계획을 발표했다.",
    )

    assert result == "current_article"


def test_decide_answer_source_rejects_unsupported_answer(monkeypatch):
    """현재 기사에 근거가 없는 답변은 현재 기사 답변으로 인정하지 않는다."""
    monkeypatch.setattr(
        model_service,
        "generate_answer",
        lambda context, question: "예산은 100억 원이다.",
    )

    result = model_service.decide_answer_source(
        "시는 사업 계획을 발표했지만 예산은 공개하지 않았다.",
        "예산은 얼마야?",
    )

    assert result == {
        "source": "organization",
        "answer": None,
    }


def test_check_call_rejects_unknown_tool():
    """등록되지 않은 도구는 거부한다."""
    result = tools._check_call(
        {"name": "unknown_tool", "arguments": {}},
        "우리 회사 기사 몇 개야?",
    )

    assert result is None


def test_check_call_rejects_invalid_period():
    """허용되지 않은 기간은 거부한다."""
    result = tools._check_call(
        {
            "name": "count_articles",
            "arguments": {"period": "tomorrow"},
        },
        "우리 회사 기사 몇 개야?",
    )

    assert result is None


def test_check_call_rejects_author_not_in_question():
    """질문에 없는 기자 이름을 임의로 사용하면 거부한다."""
    result = tools._check_call(
        {
            "name": "count_articles_by_author",
            "arguments": {"author": "김가짜", "period": "all"},
        },
        "우리 회사 기사 몇 개야?",
    )

    assert result is None


def test_check_call_accepts_author_in_question():
    """질문에 실제로 언급된 기자 이름은 정상 처리한다."""
    result = tools._check_call(
        {
            "name": "count_articles_by_author",
            "arguments": {"author": "김바다", "period": "all"},
        },
        "김바다 기자가 쓴 기사 몇 개야?",
    )

    assert result is not None
    function, arguments = result

    assert function is tools._tool_count_articles_by_author
    assert arguments == {"author": "김바다", "period": "all"}


def test_check_call_converts_department_to_category_count():
    """정치부 같은 부서 질문은 해당 분야 기사 수 조회로 변환한다."""
    result = tools._check_call(
        {
            "name": "count_articles_by_author",
            "arguments": {"author": "정치부", "period": "all"},
        },
        "정치부 기사 몇 개야?",
    )

    assert result is not None
    function, arguments = result

    assert function is tools._tool_count_articles
    assert arguments == {"period": "all", "category": "정치"}


def test_check_call_converts_recent_list_to_count():
    """최근 기사 목록 도구를 골랐더라도 질문이 개수를 물으면 개수 조회로 바꾼다."""
    result = tools._check_call(
        {
            "name": "list_recent_articles",
            "arguments": {"period": "all"},
        },
        "최근 회사 기사 몇 개야?",
    )

    assert result is not None
    function, arguments = result

    assert function is tools._tool_count_articles
    assert arguments == {"period": "all"}


def test_check_call_rejects_unknown_category():
    """지원하지 않는 분야는 거부한다."""
    result = tools._check_call(
        {
            "name": "count_articles",
            "arguments": {"period": "all", "category": "건강"},
        },
        "우리 회사 기사 몇 개야?",
    )

    assert result is None


class FakeSession:
    """실제 DB 연결 없이 SessionLocal의 컨텍스트 관리자 동작을 흉내 낸다."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_query_company_data_dispatches_validated_tool(monkeypatch):
    """유효한 LLM 도구 선택이 검증을 거쳐 조회 함수까지 전달된다."""
    calls = {}

    def fake_tool(session, organization_id, period="all", category=None):
        calls["execution"] = (organization_id, period, category)
        return "회사 기사 12건입니다."

    monkeypatch.setattr(tools, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        tools,
        "_find_organization_id",
        lambda session, article_id: 123,
    )
    monkeypatch.setitem(
        tools._COMPANY_DATA_FUNCTIONS,
        "count_articles",
        fake_tool,
    )
    monkeypatch.setattr(
        model_service,
        "select_company_data_tool",
        lambda question: {
            "name": "count_articles",
            "arguments": {"period": "all"},
        },
    )

    result = tools.query_company_data("우리 회사 기사 몇 개야?", 10)

    assert result == "회사 기사 12건입니다."
    assert calls["execution"] == (123, "all", None)


def test_query_company_data_returns_empty_without_organization(monkeypatch):
    """기사에 연결된 조직을 찾을 수 없으면 조회를 실행하지 않는다."""
    monkeypatch.setattr(tools, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        tools,
        "_find_organization_id",
        lambda session, article_id: None,
    )

    def unexpected_select(question):
        pytest.fail("조직이 없으면 LLM 도구 선택을 실행하면 안 됩니다.")

    monkeypatch.setattr(
        model_service,
        "select_company_data_tool",
        unexpected_select,
    )

    result = tools.query_company_data("우리 회사 기사 몇 개야?", 10)

    assert result == ""


def test_query_company_data_uses_fallback_when_selection_invalid(monkeypatch):
    """LLM 도구 선택을 읽을 수 없으면 키워드 규칙으로 대체한다."""
    calls = {}

    def fake_tool(session, organization_id, period="all", category=None):
        calls["execution"] = (organization_id, period)
        return "키워드 규칙으로 조회했습니다."

    monkeypatch.setattr(tools, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        tools,
        "_find_organization_id",
        lambda session, article_id: 456,
    )
    monkeypatch.setattr(
        model_service,
        "select_company_data_tool",
        lambda question: None,
    )
    monkeypatch.setattr(
        tools,
        "_fallback_call",
        lambda question: (fake_tool, {"period": "today"}),
    )

    result = tools.query_company_data("오늘 회사 기사 몇 개야?", 20)

    assert result == "키워드 규칙으로 조회했습니다."
    assert calls["execution"] == (456, "today")


def test_search_web_results_success(monkeypatch):
    """웹 검색 성공 시 결과를 정리하고 본문 길이를 제한한다."""
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    calls = {}
    content = "가" * (tools.WEB_CONTENT_MAX + 20)

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "title": "검색 결과",
                        "url": "https://example.com/article",
                        "content": content,
                    },
                    {
                        "title": "내용 없는 결과",
                        "url": "https://example.com/empty",
                        "content": "",
                    },
                ]
            }

    def fake_post(url, headers, json, timeout):
        calls["url"] = url
        calls["headers"] = headers
        calls["json"] = json
        calls["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(tools.httpx, "post", fake_post)

    result = tools._search_web_results("테스트 검색어")

    assert calls["url"] == tools.TAVILY_URL
    assert calls["headers"] == {"Authorization": "Bearer test-key"}
    assert calls["json"]["query"] == "테스트 검색어"
    assert calls["json"]["max_results"] == tools.WEB_MAX_RESULTS

    assert len(result) == 1
    assert result[0]["title"] == "검색 결과"
    assert result[0]["content"] == content[:tools.WEB_CONTENT_MAX]


def test_search_web_results_keyless_mode(monkeypatch):
    """API 키가 없으면 keyless 모드로 요청한다."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": []}

    def fake_post(url, headers, json, timeout):
        calls["headers"] = headers
        return FakeResponse()

    monkeypatch.setattr(tools.httpx, "post", fake_post)

    result = tools._search_web_results("검색어")

    assert calls["headers"] == {
        "X-Tavily-Access-Mode": "keyless"
    }
    assert result == []


def test_search_web_results_network_error(monkeypatch):
    """네트워크 오류가 발생하면 예외 대신 빈 결과를 반환한다."""
    def fake_post(*args, **kwargs):
        raise tools.httpx.ConnectError("network error")

    monkeypatch.setattr(tools.httpx, "post", fake_post)

    result = tools._search_web_results("검색어")

    assert result == []


def test_search_web_formats_results(monkeypatch):
    """웹 검색 결과를 제목과 내용으로 구성된 문맥 문자열로 만든다."""
    monkeypatch.setattr(
        tools,
        "_search_web_results",
        lambda query: [
            {
                "title": "첫 번째 기사",
                "url": "https://example.com/1",
                "content": "첫 번째 내용",
            },
            {
                "title": "두 번째 기사",
                "url": "https://example.com/2",
                "content": "두 번째 내용",
            },
        ],
    )

    result = tools.search_web("검색어")

    assert result == (
        "첫 번째 기사\n첫 번째 내용\n\n"
        "두 번째 기사\n두 번째 내용"
    )
