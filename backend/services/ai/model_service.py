import os
import re
import threading
from contextlib import nullcontext
from pathlib import Path


# ── 설정 ─────────────────────────────────────────────

BASE_MODEL = "Qwen/Qwen3-1.7B"

# 어댑터 위치: 환경 변수(.env) SUMMARY_ADAPTER_PATH, QA_ADAPTER_PATH가 있으면 그걸 쓰고, 없으면 기본 폴더
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_ADAPTER_DIR = _BACKEND_DIR / "fine_tuning" / "adapters"   # 위치는 팀 결정 후 확정

MAX_NEW_TOKENS = {
    "summary": 150,          # 학습 config와 같음
    "answer": 150,           # 학습 config와 같음
    "formatted_article": 1024,
    "evaluation_item": 100,
    "keyword_tags": 100,
    "titles": 200,
    "article_ideas": 300,
}

# 생성 설정: "greedy"는 같은 입력이면 같은 출력, "sampling"은 Qwen3 공식 권장값(생각 모드 끔)
GENERATION_OPTIONS = {
    "greedy": {"do_sample": False, "temperature": None, "top_p": None, "top_k": None},
    "sampling": {"do_sample": True, "temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0},
}

# 기능별 생성 설정. 요약·QA는 정답이 정해진 작업이라 greedy로 둔다
# 10/15 가상 기사 비교(샘플링 시드 5개)에서 사실 오류가 늘어 나머지도 greedy로 둔다
GENERATION_MODE = {
    "summary": "greedy",
    "answer": "greedy",
    "formatted_article": "greedy",
    "evaluation_item": "greedy",
    "keyword_tags": "greedy",
    "titles": "greedy",
    "article_ideas": "greedy",
}

EVALUATION_VERDICTS = ("충족", "미흡", "해당 없음")


class ModelOutputError(Exception):
    """모델 출력이 정해진 형식이 아니어서 읽을 수 없음."""


# ── 모델 불러오기·생성 ─────────────────────────────────

_model = None
_tokenizer = None
_device = None
_lock = threading.Lock()


def _select_device_and_dtype():
    """
    실행 환경에 맞는 장치와 정밀도를 고른다.
    환경 변수(.env) MODEL_DEVICE(cuda/mps/cpu)로 장치를 직접 정할 수 있다.
    """
    import torch

    device = os.getenv("MODEL_DEVICE")
    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

    if device == "cuda":
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    elif device == "mps":
        dtype = torch.float16
    else:
        dtype = torch.float32
    return device, dtype


def _adapter_path(name: str) -> Path:
    path = Path(os.getenv(f"{name.upper()}_ADAPTER_PATH", _DEFAULT_ADAPTER_DIR / name))
    if not (path / "adapter_config.json").exists():
        raise FileNotFoundError(
            f"{name} 어댑터를 찾을 수 없습니다: {path} "
            f"(환경 변수 {name.upper()}_ADAPTER_PATH 또는 기본 폴더를 확인하세요)"
        )
    return path


def _load():
    """기본 모델과 어댑터 2개를 처음 한 번만 불러온다."""
    global _model, _tokenizer, _device
    if _model is not None:
        return _model, _tokenizer

    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device, dtype = _select_device_and_dtype()
    load_options = {"dtype": dtype}

    # 환경 변수(.env) MODEL_QUANTIZE=4bit: 메모리가 작은 NVIDIA GPU용. bitsandbytes가 없으면 그대로 진행
    if os.getenv("MODEL_QUANTIZE") == "4bit" and device == "cuda":
        try:
            from transformers import BitsAndBytesConfig
            load_options["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=dtype
            )
            load_options["device_map"] = {"": 0}
        except ImportError:
            pass

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, **load_options)
    if "device_map" not in load_options:
        model = model.to(device)

    model = PeftModel.from_pretrained(model, _adapter_path("summary"), adapter_name="summary")
    model.load_adapter(_adapter_path("qa"), adapter_name="qa")
    model.eval()

    _model, _tokenizer, _device = model, tokenizer, device
    return _model, _tokenizer


def _build_prompt(tokenizer, messages: list[dict]) -> str:
    """메시지를 모델 입력 문자열로 바꾼다. 생각 모드를 끈다."""
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


def _generate(messages: list[dict], adapter: str | None, feature: str) -> str:
    """
    adapter가 "summary"/"qa"면 그 어댑터로, None이면 기본 모델로 생성한다.
    feature(기능 이름)로 최대 토큰 수(MAX_NEW_TOKENS)와 생성 설정(GENERATION_MODE)을 고른다.
    어댑터 전환은 모델 전체 상태라 한 번에 한 요청만 생성한다.
    """
    import torch

    with _lock:
        model, tokenizer = _load()
        prompt = _build_prompt(tokenizer, messages)
        inputs = tokenizer(prompt, return_tensors="pt").to(_device)

        if adapter is None:
            context = model.disable_adapter()
        else:
            model.set_adapter(adapter)
            context = nullcontext()

        with context, torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS[feature],
                **GENERATION_OPTIONS[GENERATION_MODE[feature]],
            )

        generated = output[0][inputs["input_ids"].shape[-1]:]
        text = tokenizer.decode(generated, skip_special_tokens=True)
    return _clean(text)


# ── 프롬프트 ──────────────────────────────────────────

# 요약·QA: 학습 코드(fine_tuning/*/training.py)와 같은 문구. 바꾸면 어댑터 성능이 떨어진다.
SUMMARY_TEMPLATE = (
    "다음 원문의 핵심 내용을 한국어로 간결하게 요약하세요. "
    "원문에 없는 사실은 추가하지 마세요.\n\n"
    "### 원문 텍스트:\n{passage}"
)

QA_TEMPLATE = (
    "주어진 뉴스 본문을 읽고 질문에 답하세요. "
    "정답만 간결하게 답하세요. /no_think\n\n"
    "뉴스 본문:\n{context}\n\n"
    "질문:\n{question}"
)

# 기본 모델 기능 공통
SYSTEM_PROMPT = (
    "당신은 언론사 기자의 기사 작성을 돕는 편집 보조 도구입니다.\n"
    "- 주어진 기사에 있는 내용만 사용하세요. 기사에 없는 사실, 숫자, 평가하는 말을 더하지 마세요.\n"
    "- 기사 속 인물이나 단체의 의견은 누구의 의견인지 밝히고, 사실처럼 바꾸지 마세요.\n"
    "- 지시한 형식으로만 한국어로 답하고, 다른 말은 덧붙이지 마세요."
)

FORMATTED_ARTICLE_TEMPLATE = (
    "기사:\n{article}\n\n"
    "템플릿:\n{template}\n\n"
    "위 기사를 템플릿의 항목 순서대로 다시 작성하세요.\n"
    "- 템플릿의 모든 항목을 빠짐없이 쓰세요. 각 항목에는 그 항목에 맞는 내용만 쓰세요.\n"
    "- 항목에 맞는 내용이 기사에 없으면 그 항목에는 (기사에 없음)이라고만 쓰세요.\n"
    "- 같은 문장을 여러 항목에 반복하지 마세요.\n"
    "- 다시 작성한 기사만 출력하세요."
)

EVALUATION_ITEM_TEMPLATE = (
    "기사:\n{article}\n\n"
    "작성 기준: {title}\n"
    "기준 설명: {description}\n\n"
    "위 기사가 작성 기준을 지켰는지 기사 본문만 보고 판단하세요.\n"
    "판정은 아래 셋 중 하나입니다.\n"
    "- 충족: 기준을 지켰다\n"
    "- 미흡: 기준을 지키지 못했다\n"
    "- 해당 없음: 기사 본문만으로는 판단할 수 없다\n"
    "반드시 아래 형식으로만 답하세요.\n"
    "판정: 충족, 미흡, 해당 없음 중 하나\n"
    "이유: 판단 근거가 된 기사 내용을 담은 짧은 한 문장"
)

KEYWORD_TAGS_TEMPLATE = (
    "기사:\n{article}\n\n"
    "위 기사의 핵심 키워드를 5개 뽑으세요.\n"
    "반드시 아래 형식처럼 쉼표로 구분한 한 줄로만 답하세요.\n"
    "키워드1, 키워드2, 키워드3, 키워드4, 키워드5"
)

TITLES_TEMPLATE = (
    "기사:\n{article}\n\n"
    "위 기사에 어울리는 제목과 부제목을 3개 추천하세요.\n"
    "- 제목은 짧고 핵심이 드러나게 작성하세요.\n"
    "- 부제목은 제목 내용을 이어서 보충하는 한 문장으로 작성하세요.\n"
    "- 기사에 있는 단어들로 만드세요.\n"
    "- 세 제목은 서로 다른 관점으로 작성하세요.\n"
    "반드시 아래 형식으로만 답하세요.\n"
    "1. 제목: (제목) / 부제목: (부제목)\n"
    "2. 제목: (제목) / 부제목: (부제목)\n"
    "3. 제목: (제목) / 부제목: (부제목)"
)

ARTICLE_IDEAS_TEMPLATE = (
    "기사:\n{article}\n\n"
    "위 기사에 이어 기자가 직접 취재할 후속 기사 주제를 3개 제안하세요.\n"
    "- 각 주제는 취재할 대상과 내용이 드러나는 한 문장으로 작성하세요.\n"
    "- 문장은 \"~을 취재한다\"로 끝내세요.\n"
    "- 기사에 없는 새로운 사실을 확인하는 주제로 작성하세요.\n"
    "반드시 아래 형식으로만 답하세요.\n"
    "1. (취재 주제)\n"
    "2. (취재 주제)\n"
    "3. (취재 주제)"
)


# 예시 답변 (few-shot): 테스트 기사와 겹치지 않는 가상 기사. 모델이 "어떻게 답하는지" 보고 따라 하게 한다
_EXAMPLE_ARTICLE = (
    "새봄구립도서관은 다음 달 1일부터 평일 운영 시간을 오후 10시까지 2시간 늘린다고 20일 밝혔다. "
    "이용자 설문에서 응답자의 68%가 저녁 시간 연장을 원했다는 결과를 반영한 조치다. "
    "주말 운영 시간은 지금과 같다. "
    "김바다 관장은 \"퇴근 후에도 도서관을 편하게 이용할 수 있게 하겠다\"고 말했다."
)

FORMATTED_ARTICLE_EXAMPLE = {
    "template": "[제목]\n[리드]\n[본문]\n[인용]\n[향후 계획]",
    "answer": (
        "[제목] 새봄구립도서관, 평일 운영 오후 10시까지 연장\n\n"
        "[리드] 새봄구립도서관은 다음 달 1일부터 평일 운영 시간을 오후 10시까지 2시간 늘린다고 20일 밝혔다.\n\n"
        "[본문] 이용자 설문에서 응답자의 68%가 저녁 시간 연장을 원했다는 결과를 반영한 조치다. "
        "주말 운영 시간은 지금과 같다.\n\n"
        "[인용] 김바다 관장은 \"퇴근 후에도 도서관을 편하게 이용할 수 있게 하겠다\"고 말했다.\n\n"
        "[향후 계획] (기사에 없음)"
    ),
}

# 판정 세 가지를 하나씩 보여 준다. 기준은 실제 지침 항목과 겹치지 않게 만든 것
EVALUATION_EXAMPLES = [
    {
        "item": {"title": "날짜는 구체적으로", "description": "일정은 요일이나 '최근' 대신 구체적인 날짜로 씁니다."},
        "answer": "판정: 충족\n이유: \"다음 달 1일부터\", \"20일 밝혔다\"처럼 날짜를 구체적으로 썼다.",
    },
    {
        "item": {"title": "수치의 출처 명시", "description": "조사 결과를 쓸 때는 조사 기관과 조사 시기를 함께 밝힙니다."},
        "answer": "판정: 미흡\n이유: 설문 결과 68%를 쓰면서 조사 기관과 시기를 밝히지 않았다.",
    },
    {
        "item": {"title": "그래픽 자료 제공", "description": "수치가 많은 기사는 표나 그래프를 함께 제공합니다."},
        "answer": "판정: 해당 없음\n이유: 표나 그래프를 함께 제공했는지는 기사 본문만으로 알 수 없다.",
    },
]


def _with_examples(messages: list[dict], examples: list[tuple[str, str]]) -> list[dict]:
    """system 메시지 뒤에 (예시 질문, 예시 답변) 대화를 끼워 넣는다."""
    turns = []
    for question, answer in examples:
        turns += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
    return messages[:1] + turns + messages[1:]


def _user_messages(content: str) -> list[dict]:
    return [{"role": "user", "content": content}]


def _system_messages(content: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}]


def _summary_messages(passage: str) -> list[dict]:
    return _user_messages(SUMMARY_TEMPLATE.format(passage=passage))


def _answer_messages(context: str, question: str) -> list[dict]:
    return _user_messages(QA_TEMPLATE.format(context=context, question=question))


def _formatted_article_messages(article: str, template: str) -> list[dict]:
    example = FORMATTED_ARTICLE_TEMPLATE.format(
        article=_EXAMPLE_ARTICLE, template=FORMATTED_ARTICLE_EXAMPLE["template"]
    )
    return _with_examples(
        _system_messages(FORMATTED_ARTICLE_TEMPLATE.format(article=article, template=template)),
        [(example, FORMATTED_ARTICLE_EXAMPLE["answer"])],
    )


def _evaluation_prompt(article: str, item: dict) -> str:
    return EVALUATION_ITEM_TEMPLATE.format(
        article=article, title=item["title"], description=item.get("description", "")
    )


def _evaluation_item_messages(article: str, item: dict) -> list[dict]:
    return _with_examples(
        _system_messages(_evaluation_prompt(article, item)),
        [(_evaluation_prompt(_EXAMPLE_ARTICLE, ex["item"]), ex["answer"]) for ex in EVALUATION_EXAMPLES],
    )


def _keyword_tags_messages(article: str) -> list[dict]:
    return _system_messages(KEYWORD_TAGS_TEMPLATE.format(article=article))


def _titles_messages(article: str) -> list[dict]:
    return _system_messages(TITLES_TEMPLATE.format(article=article))


def _article_ideas_messages(article: str) -> list[dict]:
    return _system_messages(ARTICLE_IDEAS_TEMPLATE.format(article=article))


# ── 결과 정리 ─────────────────────────────────────────

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
_NUMBERED_LINE = re.compile(r"^\s*\d+[.)]\s*(.+)$")
_TITLE_LINE = re.compile(r"제목\s*:\s*(.+?)\s*/\s*부제목\s*:\s*(.+)")
_VERDICT = re.compile(r"판정\s*:\s*(충족|미흡|해당\s*없음)")
_VERDICT_AT_START = re.compile(r"^\s*(충족|미흡|해당\s*없음)")   # "판정:" 없이 판정부터 쓴 경우
_REASON = re.compile(r"이유\s*:\s*(.+)")


def _clean(text: str) -> str:
    """출력에 생각 블록이 섞여 있으면 지우고 앞뒤 공백을 정리한다."""
    return _THINK_BLOCK.sub("", text).strip()


def _parse_keyword_tags(text: str) -> list[str]:
    tags = []
    for part in re.split(r"[,\n]", text):
        tag = part.strip().lstrip("#").strip()
        tag = re.sub(r"^\d+[.)]\s*", "", tag)
        if tag and tag not in tags:
            tags.append(tag)
    if not tags:
        raise ModelOutputError(f"키워드를 읽을 수 없습니다: {text!r}")
    return tags


def _parse_titles(text: str) -> list[dict]:
    titles = []
    for line in text.splitlines():
        match = _TITLE_LINE.search(line)
        if match:
            titles.append({"title": match.group(1).strip(), "subtitle": match.group(2).strip()})
    if not titles:
        raise ModelOutputError(f"제목을 읽을 수 없습니다: {text!r}")
    return titles


def _parse_numbered(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        match = _NUMBERED_LINE.match(line)
        if match:
            items.append(match.group(1).strip())
    if not items:
        raise ModelOutputError(f"목록을 읽을 수 없습니다: {text!r}")
    return items


def _parse_verdict(text: str) -> dict:
    verdict = _VERDICT.search(text) or _VERDICT_AT_START.search(text)
    reason = _REASON.search(text)
    if verdict is None:
        return {"verdict": "판정 실패", "reason": text}
    return {
        "verdict": re.sub(r"\s+", " ", verdict.group(1)),
        "reason": reason.group(1).strip() if reason else "",
    }


# ── 기능 함수 ─────────────────────────────────────────

def generate_summary(article: str) -> str:
    """요약 (요약 어댑터)."""
    return _generate(_summary_messages(article), "summary", "summary")


def generate_answer(context: str, question: str) -> str:
    """질의응답 (QA 어댑터)."""
    return _generate(_answer_messages(context, question), "qa", "answer")


def generate_formatted_article(article: str, template: str) -> str:
    """템플릿 형식에 맞춰 기사 수정."""
    return _generate(
        _formatted_article_messages(article, template), None, "formatted_article"
    )


def generate_article_evaluation(article: str, guideline: list[dict]) -> dict:
    """
    회사 지침 기반 기사 평가. 
    지침 항목마다 따로 판단한다.
    guideline: [{"title": "항목 제목", "description": "항목 설명"}, ...]
    """
    items = []
    for item in guideline:
        raw = _generate(
            _evaluation_item_messages(article, item), None, "evaluation_item"
        )
        items.append({"title": item["title"], **_parse_verdict(raw)})

    summary = {verdict: 0 for verdict in (*EVALUATION_VERDICTS, "판정 실패")}
    for item in items:
        summary[item["verdict"]] += 1
    return {"items": items, "summary": summary}


def generate_keyword_tags(article: str) -> list[str]:
    """키워드/태그 추천."""
    raw = _generate(_keyword_tags_messages(article), None, "keyword_tags")
    return _parse_keyword_tags(raw)


def generate_titles(article: str) -> list[dict]:
    """제목·부제목 추천. [{"title": ..., "subtitle": ...}, ...]"""
    raw = _generate(_titles_messages(article), None, "titles")
    return _parse_titles(raw)


def generate_article_ideas(article: str) -> list[str]:
    """후속 기사 아이디어 추천."""
    raw = _generate(_article_ideas_messages(article), None, "article_ideas")
    return _parse_numbered(raw)
