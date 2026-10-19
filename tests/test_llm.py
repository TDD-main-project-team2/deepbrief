import ast
import sys
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.services.ai import model_service


ARTICLE = (
    "새봄신문\n"
    "입력 2026.10.14. 오후 3:20\n"
    "한빛시는 내년 3월부터 시내버스 120대를 전기버스로 바꾼다고 14일 밝혔다. "
    "교체 비용은 모두 960억 원이다.\n"
    "김바다 기자"
)

TOOL_CALL = '<tool_call>\n{"name": "count_articles", "arguments": {"period": "all"}}\n</tool_call>'


def load_training_formatter(relative_path):
    """학습 코드(training.py)에서 format_training_example 함수만 꺼낸다."""
    path = Path(model_service.__file__).resolve().parents[2] / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "format_training_example")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["format_training_example"]


def use_fake_model(monkeypatch, decoded):
    """_generate가 실제 모델 대신 가짜 모델·토크나이저를 쓰게 한다 (torch도 가짜로 바꿔 GPU 없이 실행)."""
    inputs = {"input_ids": SimpleNamespace(shape=(1, 3))}   # 입력 토큰 3개
    tokenizer = Mock()
    tokenizer.apply_chat_template.return_value = "프롬프트"
    tokenizer.return_value.to.return_value = inputs
    tokenizer.decode.return_value = decoded
    model = Mock()
    model.disable_adapter.return_value = nullcontext()
    model.generate.return_value = [[1, 2, 3, 7, 8]]   # 입력 토큰 3개 + 생성 토큰 2개

    monkeypatch.setattr(model_service, "_load", lambda: (model, tokenizer))
    monkeypatch.setattr(model_service, "_device", "cpu")
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(inference_mode=nullcontext))
    return model, tokenizer


def test_generate_switches_to_requested_adapter(monkeypatch):
    """어댑터 이름을 주면 그 어댑터로 바꾸고, 기능별 최대 토큰 수와 greedy 설정으로 생성한다."""
    model, tokenizer = use_fake_model(monkeypatch, "  120대  ")

    result = model_service._generate([{"role": "user", "content": "질문"}], "qa", "answer")

    assert result == "120대"
    model.set_adapter.assert_called_once_with("qa")
    model.disable_adapter.assert_not_called()
    options = model.generate.call_args.kwargs
    assert options["max_new_tokens"] == model_service.MAX_NEW_TOKENS["answer"]
    assert options["do_sample"] is False
    tokenizer.decode.assert_called_once_with([7, 8], skip_special_tokens=True)   # 생성한 부분만 읽는다


def test_generate_disables_adapter_for_base_model(monkeypatch):
    """어댑터가 None이면 기본 모델로 생성하고, 생각 모드를 끄며, 출력의 생각 블록을 지운다."""
    model, tokenizer = use_fake_model(monkeypatch, "<think>\n\n</think>\n\n결과")
    tools = [{"type": "function"}]
    messages = [{"role": "user", "content": "질문"}]

    result = model_service._generate(messages, None, "titles", tools=tools)

    assert result == "결과"
    model.disable_adapter.assert_called_once()
    model.set_adapter.assert_not_called()
    max_new_tokens = model.generate.call_args.kwargs["max_new_tokens"]
    assert max_new_tokens == model_service.MAX_NEW_TOKENS["titles"]
    template_options = tokenizer.apply_chat_template.call_args.kwargs
    assert template_options["enable_thinking"] is False
    assert template_options["tools"] == tools


def test_summary_messages_match_training():
    """요약 입력이 학습 코드(summary/training.py)의 입력과 글자까지 같다 (다르면 어댑터 성능이 떨어짐)."""
    format_training_example = load_training_formatter("fine_tuning/summary/training.py")
    sample = {"Meta(Refine)": {"passage": ARTICLE}, "Annotation": {"summary3": "요약"}}
    expected = format_training_example(sample)["prompt"]

    assert model_service._summary_messages(ARTICLE) == expected


def test_answer_messages_match_training():
    """질의응답 입력이 학습 코드(qa/training.py)의 입력과 글자까지 같다."""
    format_training_example = load_training_formatter("fine_tuning/qa/training.py")
    sample = {"context": ARTICLE, "question": "몇 대를 바꿔?", "answer": "120대"}

    expected = format_training_example(sample)["prompt"]

    assert model_service._answer_messages(ARTICLE, "몇 대를 바꿔?") == expected


def test_generate_summary_uses_summary_adapter(monkeypatch):
    """요약은 요약 어댑터로 생성하고 앞뒤 공백을 지운 문자열을 돌려준다."""
    generate = Mock(return_value="  한빛시가 전기버스 120대를 도입한다.  ")
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_summary(ARTICLE)

    assert result == "한빛시가 전기버스 120대를 도입한다."
    messages, adapter, feature = generate.call_args.args
    assert adapter == "summary"
    assert ARTICLE in messages[-1]["content"]


def test_generate_summary_empty_output(monkeypatch):
    """모델 출력이 비면 빈 메시지 대신 안내 문구를 돌려준다 (messages.content는 빈 값을 허용하지 않음)."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value="   "))

    result = model_service.generate_summary(ARTICLE)

    assert result == model_service.EMPTY_OUTPUT_MESSAGE


def test_generate_summary_invalid_article_type(monkeypatch):
    """기사 본문 문자열이나 body·text가 있는 객체가 아니면 모델을 부르지 않고 TypeError를 낸다."""
    generate = Mock()
    monkeypatch.setattr(model_service, "_generate", generate)

    with pytest.raises(TypeError):
        model_service.generate_summary(123)

    generate.assert_not_called()


def test_generate_answer_uses_qa_adapter(monkeypatch):
    """질의응답은 QA 어댑터로 생성한다. Article 객체도 본문(body)으로 받는다."""
    generate = Mock(return_value="120대")
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_answer(SimpleNamespace(body=ARTICLE), "몇 대를 바꿔?")

    assert result == "120대"
    messages, adapter, feature = generate.call_args.args
    assert adapter == "qa"
    assert ARTICLE in messages[-1]["content"]


def test_generate_keyword_tags_removes_marks_and_duplicates(monkeypatch):
    """키워드에서 # 표시와 중복을 지우고 쉼표로 잇는다."""
    generate = Mock(return_value="#전기버스, 한빛시, #전기버스, 교체 비용")
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_keyword_tags(ARTICLE)

    assert result == "전기버스, 한빛시, 교체 비용"


def test_generate_keyword_tags_data_invalid_format(monkeypatch):
    """원본용 키워드 함수는 읽을 수 없는 출력이면 ModelOutputError를 낸다."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value=""))

    with pytest.raises(model_service.ModelOutputError):
        model_service.generate_keyword_tags_data(ARTICLE)


def test_generate_title_formats_message(monkeypatch):
    """제목·부제목 출력을 번호 목록 메시지로 바꾼다."""
    generate = Mock(return_value="1. 제목: 한빛시, 전기버스 120대 도입 / 부제목: 내년 3월부터 교체 시작")
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_title(ARTICLE)

    assert result == "1. 한빛시, 전기버스 120대 도입\n   부제목: 내년 3월부터 교체 시작"


def test_generate_title_invalid_format_returns_raw_text(monkeypatch):
    """메시지용 제목 함수는 형식이 깨지면 오류 대신 모델 원문을 돌려준다."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value="제목을 만들 수 없습니다."))

    result = model_service.generate_title(ARTICLE)

    assert result == "제목을 만들 수 없습니다."


def test_generate_title_data_invalid_format(monkeypatch):
    """원본용 제목 함수는 형식이 깨지면 ModelOutputError를 낸다."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value="제목을 만들 수 없습니다."))

    with pytest.raises(model_service.ModelOutputError):
        model_service.generate_title_data(ARTICLE)


def test_generate_article_ideas_formats_numbered_list(monkeypatch):
    """후속 기사 아이디어를 '1. ...' 번호 목록으로 맞춘다."""
    generate = Mock(return_value="1) 충전기 설치 일정을 취재한다\n2) 기존 버스 기사 고용을 취재한다")
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_article_ideas(ARTICLE)

    assert result == "1. 충전기 설치 일정을 취재한다\n2. 기존 버스 기사 고용을 취재한다"


def test_generate_article_evaluation_counts_verdicts(monkeypatch):
    """지침 항목마다 판정하고 판정별 개수와 이유를 메시지로 만든다."""
    generate = Mock(side_effect=[
        "판정: 충족\n이유: 날짜를 구체적으로 썼다.",
        "판정: 미흡\n이유: 비용의 출처가 없다.",
    ])
    monkeypatch.setattr(model_service, "_generate", generate)
    guideline = [
        {"title": "날짜는 구체적으로", "description": "요일 대신 날짜로 씁니다."},
        {"title": "수치의 출처 명시", "description": "수치의 출처를 밝힙니다."},
    ]

    result = model_service.generate_article_evaluation(ARTICLE, guideline)

    assert result == (
        "충족 1개, 미흡 1개, 해당 없음 0개\n"
        "\n[충족] 날짜는 구체적으로\n- 이유: 날짜를 구체적으로 썼다.\n"
        "\n[미흡] 수치의 출처 명시\n- 이유: 비용의 출처가 없다."
    )


def test_generate_article_evaluation_data_failed_item(monkeypatch):
    """판정을 읽을 수 없는 항목만 '판정 실패'로 세고 나머지는 계속 평가한다."""
    generate = Mock(side_effect=["판정: 충족\n이유: 날짜를 구체적으로 썼다.", "잘 모르겠습니다."])
    monkeypatch.setattr(model_service, "_generate", generate)
    guideline = SimpleNamespace(title="작성 지침", content="1. 날짜는 구체적으로\n2. 수치의 출처 명시")

    result = model_service.generate_article_evaluation_data(ARTICLE, guideline)

    assert [item["verdict"] for item in result["items"]] == ["충족", "판정 실패"]
    assert result["summary"] == {"충족": 1, "미흡": 0, "해당 없음": 0, "판정 실패": 1}


def test_generate_formatted_article_uses_template_object(monkeypatch):
    """템플릿 수정은 DB의 Template 객체(content)를 받아 프롬프트에 넣는다."""
    generate = Mock(return_value="[제목] 전기버스 도입")
    monkeypatch.setattr(model_service, "_generate", generate)
    template = SimpleNamespace(content="[제목]\n[본문]")

    result = model_service.generate_formatted_article(ARTICLE, template)

    assert result == "[제목] 전기버스 도입"
    messages = generate.call_args.args[0]
    assert "[제목]\n[본문]" in messages[-1]["content"]


def test_generate_formatted_article_invalid_template(monkeypatch):
    """템플릿이 문자열이나 content가 있는 객체가 아니면 TypeError를 낸다."""
    monkeypatch.setattr(model_service, "_generate", Mock())

    with pytest.raises(TypeError):
        model_service.generate_formatted_article(ARTICLE, None)


@pytest.mark.parametrize("output, expected", [
    ("정치", "정치"),
    ("분야: 경제.", "경제"),
    ("문화(생활 포함)", "문화"),
    ("모르겠습니다", None),
    ("정치, 경제", None),
])
def test_generate_category(monkeypatch, output, expected):
    """정해진 분야 목록의 값만 돌려주고, 목록 밖이거나 둘 이상이면 None."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value=output))

    assert model_service.generate_category(ARTICLE) == expected


def test_generate_article_metadata(monkeypatch):
    """언론사·기자·작성일을 추출하고(직함 제거, 한국 시간) 카테고리를 함께 돌려준다."""
    generate = Mock(side_effect=[
        "언론사: 새봄신문\n기자: 김바다 기자\n작성일: 2026.10.14. 오후 3:20",   # 메타데이터
        "사회",                                                                 # 카테고리
    ])
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_article_metadata(ARTICLE)

    assert result == {
        "media": "새봄신문",
        "author": "김바다",
        "category": "사회",
        "published_at": datetime(2026, 10, 14, 15, 20, tzinfo=model_service.KST),
    }


def test_generate_article_metadata_not_in_article(monkeypatch):
    """모델이 기사에 없는 언론사·기자·날짜를 지어내면 None으로 둔다."""
    generate = Mock(side_effect=["언론사: 한빛일보\n기자: 이하늘 기자\n작성일: 2026.09.13", "사회"])
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_article_metadata(ARTICLE)

    assert result["media"] is None
    assert result["author"] is None
    assert result["published_at"] is None


def test_generate_article_metadata_invalid_media(monkeypatch):
    """언론사 칸에 기자 이름·직함이 들어오면 언론사만 None으로 둔다."""
    generate = Mock(side_effect=["언론사: 김바다 기자\n기자: 김바다 기자\n작성일: (기사에 없음)", "사회"])
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_article_metadata(ARTICLE)

    assert result["media"] is None
    assert result["author"] == "김바다"


def test_generate_article_metadata_document_result(monkeypatch):
    """업로드 결과(DocumentResult)면 OCR이 뺀 줄 중 언론사·기자 후보를 붙여 보고, 카테고리는 본문만 본다."""
    generate = Mock(side_effect=["언론사: 새봄신문\n기자: 김바다 기자\n작성일: (기사에 없음)", "사회"])
    monkeypatch.setattr(model_service, "_generate", generate)
    body = "한빛시는 내년 3월부터 시내버스 120대를 전기버스로 바꾼다고 14일 밝혔다."
    document = SimpleNamespace(text=body, meta_text=["새봄신문", "김바다 기자", "로그인 메뉴 전체보기"])

    result = model_service.generate_article_metadata(document)

    assert result["media"] == "새봄신문"
    assert result["author"] == "김바다"
    metadata_prompt = generate.call_args_list[0].args[0][-1]["content"]
    category_prompt = generate.call_args_list[1].args[0][-1]["content"]
    assert "김바다 기자" in metadata_prompt
    assert "로그인 메뉴 전체보기" not in metadata_prompt   # 잡음 줄은 버린다
    assert "새봄신문" not in category_prompt


def test_generate_article_metadata_invalid_format(monkeypatch):
    """출력 형식이 깨져도 오류를 내지 않고 None으로 둔다 (업로드가 멈추지 않게)."""
    monkeypatch.setattr(model_service, "_generate", Mock(side_effect=["찾을 수 없습니다.", "사회"]))

    result = model_service.generate_article_metadata(ARTICLE)

    assert result == {"media": None, "author": None, "category": "사회", "published_at": None}


def test_generate_duplicate_check(monkeypatch):
    """현재 기사와 비슷한 회사 기사 조각을 넣고 판정과 이유를 메시지로 만든다."""
    generate = Mock(return_value="판정: 중복 의심\n이유: 같은 전기버스 교체 발표를 다뤘다.")
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_duplicate_check(ARTICLE, "한빛시가 전기버스 120대를 도입한다.")

    assert result == "[중복 의심] 이유: 같은 전기버스 교체 발표를 다뤘다."
    messages = generate.call_args.args[0]
    assert "한빛시가 전기버스 120대를 도입한다." in messages[-1]["content"]


def test_generate_duplicate_check_without_similar_articles(monkeypatch):
    """비슷한 회사 기사 조각이 없으면 모델을 부르지 않고 안내 문구를 돌려준다."""
    generate = Mock()
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.generate_duplicate_check(ARTICLE, "")

    assert result == model_service.NO_SIMILAR_MESSAGE
    generate.assert_not_called()


def test_generate_duplicate_check_limits_similar_context(monkeypatch):
    """비슷한 조각은 정해진 글자 수까지만 조각 단위로 넣는다."""
    generate = Mock(return_value="판정: 중복 아님\n이유: 다른 사건이다.")
    monkeypatch.setattr(model_service, "_generate", generate)
    similar = "\n\n".join(["가" * 2000, "나" * 2000, "다" * 2000])

    model_service.generate_duplicate_check(ARTICLE, similar)

    prompt = generate.call_args.args[0][-1]["content"]
    assert "가" * 2000 in prompt
    assert "나" * 2000 not in prompt


def test_generate_duplicate_check_invalid_format_returns_raw_text(monkeypatch):
    """판정 형식이 깨지면 오류 대신 모델 원문을 돌려준다."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value="잘 모르겠습니다."))

    result = model_service.generate_duplicate_check(ARTICLE, "한빛시가 전기버스 120대를 도입한다.")

    assert result == "잘 모르겠습니다."


def test_decide_answer_source_current_article(monkeypatch):
    """현재 기사 조각으로 답이 되면 current_article과 답을 돌려준다."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value="120대"))

    result = model_service.decide_answer_source(ARTICLE, "몇 대를 바꿔?")

    assert result == {"source": "current_article", "answer": "120대"}


def test_decide_answer_source_not_in_context(monkeypatch):
    """답이 근거 본문에 없으면(지어낸 답) 현재 기사로 답할 수 없는 것으로 본다."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value="200대"))

    result = model_service.decide_answer_source(ARTICLE, "몇 대를 바꿔?")

    assert result == {"source": "organization", "answer": None}


def test_decide_answer_source_yes_no(monkeypatch):
    """예/아니오형 답은 본문에 그 말이 없어도 답으로 인정한다."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value="예"))

    result = model_service.decide_answer_source(ARTICLE, "전기버스로 바꿔?")

    assert result == {"source": "current_article", "answer": "예"}


def test_generate_organization_answer_not_found(monkeypatch):
    """회사 기사 조각으로도 답이 없으면 안내 문구를 돌려준다."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value=model_service.QA_NO_ANSWER))

    result = model_service.generate_organization_answer(ARTICLE, "충전기는 몇 기야?")

    assert result == model_service.NOT_FOUND_MESSAGE


def test_select_company_data_tool(monkeypatch):
    """사내 조회 도구 목록을 넘기고, 모델의 tool_call 출력을 도구 이름과 인자로 읽는다."""
    generate = Mock(return_value=(
        '<tool_call>\n'
        '{"name": "count_articles", "arguments": {"period": "last_month", "category": "정치"}}\n'
        '</tool_call>'
    ))
    monkeypatch.setattr(model_service, "_generate", generate)

    result = model_service.select_company_data_tool("지난달 정치부 기사 몇 개야?")

    assert result == {
        "name": "count_articles",
        "arguments": {"period": "last_month", "category": "정치"},
    }
    assert generate.call_args.kwargs["tools"] == model_service.COMPANY_DATA_TOOLS


@pytest.mark.parametrize("output", ["없음", "{잘못된 형식}", '{"arguments": {}}'])
def test_select_company_data_tool_no_call(monkeypatch, output):
    """도구를 호출하지 않았거나 호출을 읽을 수 없으면 None."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value=output))

    assert model_service.select_company_data_tool("탄소중립이 무슨 뜻이야?") is None


def test_classify_retrieval_scope_company_data(monkeypatch):
    """모델이 사내 조회 도구를 호출하고 질문에 사내 관련 단어가 있으면 company_data."""
    monkeypatch.setattr(model_service, "_generate", Mock(return_value=TOOL_CALL))

    assert model_service.classify_retrieval_scope("우리 회사 기사 몇 개야?", ARTICLE) == "company_data"


def test_classify_retrieval_scope_no_company_cue(monkeypatch):
    """모델이 사내 조회 도구를 골라도 질문에 사내 관련 단어가 없으면 company_data로 보내지 않는다."""
    generate = Mock(side_effect=[TOOL_CALL, model_service.QA_NO_ANSWER])
    monkeypatch.setattr(model_service, "_generate", generate)

    assert model_service.classify_retrieval_scope("탄소중립이 무슨 뜻이야?", ARTICLE) == "web"


def test_classify_retrieval_scope_current_article(monkeypatch):
    """도구를 호출하지 않고 현재 기사에서 답이 나오면 current_article."""
    monkeypatch.setattr(model_service, "_generate", Mock(side_effect=["없음", "120대"]))

    assert model_service.classify_retrieval_scope("몇 대를 바꿔?", ARTICLE) == "current_article"


def test_classify_retrieval_scope_echo_answer(monkeypatch):
    """현재 기사에서 뽑은 답이 질문에 이미 있는 말이면 답으로 보지 않고 web."""
    monkeypatch.setattr(model_service, "_generate", Mock(side_effect=["없음", "전기버스"]))

    assert model_service.classify_retrieval_scope("수소버스와 전기버스 차이가 뭐야?", ARTICLE) == "web"


def test_classify_retrieval_scope_web(monkeypatch):
    """도구를 호출하지 않고 현재 기사에서도 답이 없으면 web."""
    generate = Mock(side_effect=["없음", model_service.QA_NO_ANSWER])
    monkeypatch.setattr(model_service, "_generate", generate)

    assert model_service.classify_retrieval_scope("전기버스 배터리 수명은 보통 몇 년이야?", ARTICLE) == "web"


def test_adapter_path_missing(monkeypatch, tmp_path):
    """어댑터 폴더에 adapter_config.json이 없으면 FileNotFoundError를 낸다."""
    monkeypatch.setenv("QA_ADAPTER_PATH", str(tmp_path))

    with pytest.raises(FileNotFoundError):
        model_service._adapter_path("qa")


@pytest.mark.skip
def test_generate_summary_with_real_model():
    """실제 모델과 요약 어댑터로 요약을 만든다 (GPU와 어댑터가 필요해 기본은 건너뜀)."""
    result = model_service.generate_summary(ARTICLE)

    assert result
    assert result != model_service.EMPTY_OUTPUT_MESSAGE
