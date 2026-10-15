import os
import re
import threading
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
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
    "category": 20,
    "article_metadata": 80,
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
    "category": "greedy",
    "article_metadata": "greedy",
}

EVALUATION_VERDICTS = ("충족", "미흡", "해당 없음")

# 기사 분야. 생활 기사(건강, 여행, 음식 등)도 문화로 분류한다
ARTICLE_CATEGORIES = ("정치", "경제", "사회", "문화", "IT", "과학", "세계", "엔터테인먼트", "스포츠")
_CATEGORY_LABELS = {"문화": "문화(생활 포함)"}   # 프롬프트에만 보이는 이름. 저장 값은 ARTICLE_CATEGORIES

# QA 답변 출처. 현재 기사로 답할 수 있으면 current_article, 아니면 organization(회사 기사)
ANSWER_SOURCES = ("current_article", "organization")
# QA 어댑터가 답이 없을 때 쓰도록 학습한 문장 (qa/config.yaml의 answers.unanswerable과 같아야 함)
QA_NO_ANSWER = "주어진 기사에서 답을 찾을 수 없습니다."
# 회사 기사에서도 답을 찾지 못했을 때 사용자에게 보여 줄 문구
NOT_FOUND_MESSAGE = "관련 내용을 찾지 못했습니다."

# 작성일 시간대. 한국은 서머타임이 없어 +09:00 고정이 정확하다 (ZoneInfo는 윈도우에서 tzdata 패키지가 필요)
KST = timezone(timedelta(hours=9))


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

CATEGORY_TEMPLATE = (
    "기사:\n{article}\n\n"
    "위 기사의 분야를 아래 목록에서 하나만 고르세요.\n"
    "목록: {categories}\n"
    "- IT: 인터넷, 소프트웨어, 통신, 게임, AI 서비스처럼 정보기술 제품과 서비스\n"
    "- 과학: 연구, 실험, 학술 성과, 우주, 기초과학\n"
    "- 연구 성과가 중심이면 과학, 제품이나 서비스가 중심이면 IT를 고르세요.\n"
    "- 기업의 실적, 매출, 주가, 투자가 중심이면 IT 기업이라도 경제를 고르세요.\n"
    "반드시 목록에 있는 이름 하나만 답하세요."
)

ARTICLE_METADATA_TEMPLATE = (
    "기사:\n{article}\n\n"
    "위 기사를 쓴 언론사, 기자, 기사 입력 일시를 찾아 기사에 적힌 그대로 옮기세요.\n"
    "- 언론사와 기자는 이 기사를 쓴 곳과 사람만 쓰세요. 보통 기사 맨 앞이나 맨 끝에 있습니다.\n"
    "- 언론사는 기사를 낸 신문사, 방송사, 통신사 이름입니다.\n"
    "- 작성일은 본문 속 날짜가 아닌 기사 입력 일시를 쓰세요. 입력일과 수정일이 함께 있으면 입력일을 쓰세요.\n"
    "- 찾을 수 없는 항목에는 (기사에 없음)이라고만 쓰세요.\n"
    "반드시 아래 형식으로만 답하세요.\n"
    "언론사: (언론사 이름)\n"
    "기자: (기자 이름)\n"
    "작성일: (기사에 적힌 입력 일시)"
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

# 머리말이 붙은 예시 기사. 기자는 일부러 빼서 "(기사에 없음)"과, 본문 인물(관장)을 기자로 쓰지 않는 경우를 보여 준다
ARTICLE_METADATA_EXAMPLE = {
    "article": "새봄신문\n입력 2026.09.20. 오전 10:05  수정 2026.09.20. 오후 3:40\n" + _EXAMPLE_ARTICLE,
    "answer": "언론사: 새봄신문\n기자: (기사에 없음)\n작성일: 2026.09.20. 오전 10:05",
}


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


def _category_messages(article: str) -> list[dict]:
    categories = ", ".join(_CATEGORY_LABELS.get(c, c) for c in ARTICLE_CATEGORIES)
    return _system_messages(CATEGORY_TEMPLATE.format(article=article, categories=categories))


def _article_metadata_messages(article: str) -> list[dict]:
    example = ARTICLE_METADATA_EXAMPLE
    return _with_examples(
        _system_messages(ARTICLE_METADATA_TEMPLATE.format(article=article)),
        [(ARTICLE_METADATA_TEMPLATE.format(article=example["article"]), example["answer"])],
    )


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


_NOT_FOUND = re.compile(r"\(?\s*기사에\s*없음\s*\)?")
_META_LINE = {
    "media": re.compile(r"언론사\s*:\s*(.+)"),
    "author": re.compile(r"기자\s*:\s*(.+)"),
    "published_at": re.compile(r"작성일\s*:\s*(.+)"),
}
_EMAIL = re.compile(r"\S+@\S+")
_MAX_COLUMN_LENGTH = 255   # articles.media, author 컬럼 길이 (String(255))
_AUTHOR_TITLE = re.compile(r"\s*(선임기자|수석기자|객원기자|인턴기자|기자|특파원)$")
_DATE = re.compile(
    r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?\.?"
    r"(?:\s*(?:\([월화수목금토일]\))?\s*(오전|오후)?\s*(\d{1,2})\s*[:시]\s*(\d{2})?)?"
)


def _parse_category(text: str) -> str | None:
    """목록에 있는 분야 하나를 돌려준다. 읽을 수 없으면 None (업로드를 막지 않음)."""
    answer = re.sub(r"^\s*분야\s*:\s*", "", text).strip().strip(".").strip()
    for category in ARTICLE_CATEGORIES:
        if answer in (category, _CATEGORY_LABELS.get(category, category)):
            return category
    found = [c for c in ARTICLE_CATEGORIES if c in answer]
    return found[0] if len(found) == 1 else None


def _in_article(value: str, article: str) -> bool:
    """OCR이 띄어쓰기를 바꿀 수 있어 공백을 지우고 비교한다."""
    return re.sub(r"\s+", "", value) in re.sub(r"\s+", "", article)


def _parse_author(text: str) -> str | None:
    names = []
    for part in re.split(r"[·,/]", _EMAIL.sub("", text)):
        name = _AUTHOR_TITLE.sub("", part.strip()).strip()
        if name and name not in names:
            names.append(name)
    return ", ".join(names) or None


def _parse_published_at(text: str) -> datetime | None:
    """처음 나오는 날짜를 한국 시간으로 바꾼다. 시간이 없으면 00:00, 연도가 없거나 없는 날짜면 None."""
    match = _DATE.search(text)
    if match is None:
        return None
    year, month, day, ampm, hour, minute = match.groups()
    hour = int(hour) if hour else 0
    if ampm == "오후" and hour < 12:
        hour += 12
    elif ampm == "오전" and hour == 12:
        hour = 0
    try:
        return datetime(int(year), int(month), int(day), hour, int(minute or 0), tzinfo=KST)
    except ValueError:
        return None


def _date_in_article(value: datetime, article: str) -> bool:
    """모델이 옮긴 날짜(연·월·일)가 원문에 있는지. 표기 방식이 달라도 같은 날짜면 인정한다."""
    found = {tuple(int(x) for x in m.groups()[:3]) for m in _DATE.finditer(article)}
    return (value.year, value.month, value.day) in found


def _parse_article_metadata(text: str, article: str) -> dict:
    """언론사·기자·작성일. 없거나 원문에 없는 이름·날짜면 None."""
    values = {}
    for key, pattern in _META_LINE.items():
        match = pattern.search(text)
        value = match.group(1).strip() if match else ""
        values[key] = None if not value or _NOT_FOUND.fullmatch(value) else value

    media = values["media"]
    author = _parse_author(values["author"]) if values["author"] else None
    published_at = _parse_published_at(values["published_at"]) if values["published_at"] else None
    return {
        "media": media[:_MAX_COLUMN_LENGTH] if media and _in_article(media, article) else None,
        "author": (author[:_MAX_COLUMN_LENGTH]
                   if author and all(_in_article(n, article) for n in author.split(", ")) else None),
        "published_at": published_at if published_at and _date_in_article(published_at, article) else None,
    }


# ── 입력·결과 변환 (다른 서비스가 그대로 호출할 수 있게) ──────────────

def _article_text(article) -> str:
    """기사 본문 문자열 또는 DB의 Article 객체(.body)를 받아 본문 문자열을 돌려준다."""
    if isinstance(article, str):
        return article
    body = getattr(article, "body", None)
    if isinstance(body, str):
        return body
    raise TypeError(f"기사 본문 문자열이나 body가 있는 Article 객체가 필요합니다: {type(article).__name__}")


def _template_text(template) -> str:
    """템플릿 문자열 또는 DB의 Template 객체(.content)를 받아 템플릿 문자열을 돌려준다."""
    if isinstance(template, str):
        return template
    content = getattr(template, "content", None)
    if isinstance(content, str):
        return content
    raise TypeError(f"템플릿 문자열이나 content가 있는 Template 객체가 필요합니다: {type(template).__name__}")


_LIST_MARK = re.compile(r"^\s*(?:\d+\s*[.)]|\(\d+\)|[-•·*▪◦]|[①-⑳])\s*")


def _guideline_lines(title: str, content: str) -> list[dict]:
    """
    지침 하나(title, content)를 평가 항목 목록으로 바꾼다.
    content가 여러 줄이면 한 줄을 항목 하나로 보고, "항목: 설명"이면 콜론 앞을 항목 이름으로 쓴다.
    한 줄뿐이면 지침 전체를 항목 하나로 본다 (title = 항목, content = 설명).
    """
    lines = [_LIST_MARK.sub("", line).strip() for line in content.splitlines()]
    lines = [line for line in lines if line]
    if len(lines) <= 1:
        return [{"title": title.strip(), "description": content.strip()}]
    items = []
    for line in lines:
        name, sep, description = line.partition(":")
        items.append({"title": name.strip(), "description": description.strip()} if sep and name.strip()
                     else {"title": line, "description": ""})
    return items


def _guideline_items(guideline) -> list[dict]:
    """
    지침을 평가 항목 목록 [{"title", "description"}]으로 바꾼다. 받는 모양:
    - DB의 Guideline 객체 하나 (.title, .content)
    - Guideline 객체 여러 개의 리스트
    - [{"title", "description"}] 리스트 (그대로)
    """
    if isinstance(guideline, dict) or hasattr(guideline, "content"):
        guideline = [guideline]
    items = []
    for entry in guideline:
        if isinstance(entry, dict):
            items.append({"title": entry["title"], "description": entry.get("description", "")})
        elif isinstance(getattr(entry, "content", None), str):
            items += _guideline_lines(getattr(entry, "title", "") or "", entry.content)
        else:
            raise TypeError(f"지침 항목 dict나 title·content가 있는 Guideline 객체가 필요합니다: {type(entry).__name__}")
    return items


EMPTY_OUTPUT_MESSAGE = "결과를 생성하지 못했습니다. 다시 시도해 주세요."


def _message_text(text: str) -> str:
    """메시지로 저장할 문자열. messages.content는 빈 문자열·앞뒤 공백을 허용하지 않으므로 정리한다."""
    text = text.strip()
    return text or EMPTY_OUTPUT_MESSAGE


def _title_text(titles: list[dict]) -> str:
    return "\n".join(
        f"{i}. {t['title']}\n   부제목: {t['subtitle']}" for i, t in enumerate(titles, start=1)
    )


def _numbered_text(items: list[str]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, start=1))


def _evaluation_text(result: dict) -> str:
    counts = result["summary"]
    head = ", ".join(f"{v} {counts[v]}개" for v in EVALUATION_VERDICTS)
    if counts["판정 실패"]:
        head += f", 판정 실패 {counts['판정 실패']}개"
    lines = [head]
    for item in result["items"]:
        lines.append(f"\n[{item['verdict']}] {item['title']}")
        if item["reason"]:
            lines.append(f"- 이유: {item['reason']}")
    return "\n".join(lines)


def _is_no_answer(text: str) -> bool:
    """QA 어댑터의 "답 없음" 문장인지. 띄어쓰기·마침표 차이는 무시한다."""
    normalized = re.sub(r"[\s.]", "", text)
    return not normalized or "답을찾을수없" in normalized


_YES_NO_ANSWERS = ("예", "아니오")


def _answer_in_context(answer: str, context: str) -> bool:
    """
    답이 근거 본문에 실제로 있는지. QA 어댑터가 근거에 없는 답을 지어내는 경우를 거른다.
    공백과 끝 마침표는 무시한다. 예/아니오형 정답("예", "아니오")은 본문에 없어도 인정한다.
    """
    normalized = re.sub(r"\s+", "", answer).rstrip(".")
    if normalized in _YES_NO_ANSWERS:
        return True
    return bool(normalized) and normalized in re.sub(r"\s+", "", context)


def _usable_answer(answer: str, context: str) -> bool:
    """쓸 수 있는 답인지: "답 없음"이 아니고 근거 본문에 있는 답."""
    return not _is_no_answer(answer) and _answer_in_context(answer, context)


# ── 기능 함수 ─────────────────────────────────────────
# 메시지로 저장하는 기능은 문자열을 돌려준다 (conversation_service.save_message에 그대로 넣으면 됨).
# 목록·딕셔너리 원본이 필요하면 *_data 함수를 쓴다.
# article에는 기사 본문 문자열이나 Article 객체를 넘긴다.

def generate_summary(article) -> str:
    """요약 (요약 어댑터)."""
    return _message_text(_generate(_summary_messages(_article_text(article)), "summary", "summary"))


def generate_answer(context, question: str) -> str:
    """질의응답 (QA 어댑터). context는 RAG로 찾은 본문 조각을 이은 문자열 (Article 객체도 가능)."""
    return _message_text(_generate(_answer_messages(_article_text(context), question), "qa", "answer"))


def generate_formatted_article(article, template: str) -> str:
    """템플릿 형식에 맞춰 기사 수정. template은 템플릿 문자열 또는 DB의 Template 객체(.content)."""
    return _message_text(_generate(
        _formatted_article_messages(_article_text(article), _template_text(template)), None, "formatted_article"
    ))


def generate_article_evaluation_data(article, guideline: list[dict]) -> dict:
    """
    회사 지침 기반 기사 평가 (원본). 지침 항목마다 따로 판단한다.
    guideline: DB의 Guideline 객체(하나 또는 리스트, content가 여러 줄이면 한 줄 = 항목 하나)
               또는 [{"title": "항목 제목", "description": "항목 설명"}, ...]
    반환: {"items": [{"title", "verdict", "reason"}, ...], "summary": {"충족": n, "미흡": n, "해당 없음": n, "판정 실패": n}}
    """
    text = _article_text(article)
    items = []
    for item in _guideline_items(guideline):
        raw = _generate(_evaluation_item_messages(text, item), None, "evaluation_item")
        items.append({"title": item["title"], **_parse_verdict(raw)})

    summary = {verdict: 0 for verdict in (*EVALUATION_VERDICTS, "판정 실패")}
    for item in items:
        summary[item["verdict"]] += 1
    return {"items": items, "summary": summary}


def generate_article_evaluation(article, guideline: list[dict]) -> str:
    """회사 지침 기반 기사 평가 (메시지용 문자열). 집계 한 줄 + 항목별 판정과 이유."""
    return _message_text(_evaluation_text(generate_article_evaluation_data(article, guideline)))


def generate_keyword_tags_data(article) -> list[str]:
    """키워드/태그 추천 (원본 목록). 형식이 깨지면 ModelOutputError."""
    raw = _generate(_keyword_tags_messages(_article_text(article)), None, "keyword_tags")
    return _parse_keyword_tags(raw)


def generate_keyword_tags(article) -> str:
    """키워드/태그 추천 (메시지용 문자열). 예: "가람시, 소상공인, 전기요금" """
    raw = _generate(_keyword_tags_messages(_article_text(article)), None, "keyword_tags")
    try:
        return _message_text(", ".join(_parse_keyword_tags(raw)))
    except ModelOutputError:
        return _message_text(raw)


def generate_title_data(article) -> list[dict]:
    """제목·부제목 추천 (원본). [{"title": ..., "subtitle": ...}, ...] 형식이 깨지면 ModelOutputError."""
    raw = _generate(_titles_messages(_article_text(article)), None, "titles")
    return _parse_titles(raw)


def generate_title(article) -> str:
    """제목·부제목 추천 (메시지용 문자열). "1. 제목\n   부제목: ..." 3개"""
    raw = _generate(_titles_messages(_article_text(article)), None, "titles")
    try:
        return _message_text(_title_text(_parse_titles(raw)))
    except ModelOutputError:
        return _message_text(raw)


def generate_article_ideas_data(article) -> list[str]:
    """후속 기사 아이디어 추천 (원본 목록). 형식이 깨지면 ModelOutputError."""
    raw = _generate(_article_ideas_messages(_article_text(article)), None, "article_ideas")
    return _parse_numbered(raw)


def generate_article_ideas(article) -> str:
    """후속 기사 아이디어 추천 (메시지용 문자열). "1. ...\n2. ...\n3. ..." """
    raw = _generate(_article_ideas_messages(_article_text(article)), None, "article_ideas")
    try:
        return _message_text(_numbered_text(_parse_numbered(raw)))
    except ModelOutputError:
        return _message_text(raw)


def generate_category(article) -> str | None:
    """기사 분야 분류. ARTICLE_CATEGORIES 중 하나, 읽을 수 없으면 None."""
    raw = _generate(_category_messages(_article_text(article)), None, "category")
    return _parse_category(raw)


def generate_article_metadata(article) -> dict:
    """
    기사 메타데이터 4개 (Article 컬럼 이름과 같음). 언론사·기자·작성일은 기사에서 추출하고,
    카테고리는 분류한다 (모델 호출 2번). 없으면 None.
    {"media": str | None, "author": str | None, "category": str | None,
     "published_at": datetime(한국 시간) | None}
    """
    text = _article_text(article)
    raw = _generate(_article_metadata_messages(text), None, "article_metadata")
    found = _parse_article_metadata(raw, text)
    return {
        "media": found["media"],
        "author": found["author"],
        "category": generate_category(text),
        "published_at": found["published_at"],
    }


def decide_answer_source(context, question: str) -> dict:
    """
    QA 1단계. 현재 기사에서 찾은 본문 조각으로 답할 수 있는지 판단하고, 되면 답까지 만든다 (QA 어댑터 1번).
    "답 없음"이거나 답이 본문에 없으면(지어낸 답) 답할 수 없는 것으로 본다.
    {"source": "current_article", "answer": 답}  또는  {"source": "organization", "answer": None}
    organization이면 회사 기사 조각을 찾아 generate_organization_answer로 넘긴다.
    """
    text = _article_text(context)
    answer = generate_answer(text, question)
    if not _usable_answer(answer, text):
        return {"source": "organization", "answer": None}
    return {"source": "current_article", "answer": answer}


def generate_organization_answer(context, question: str) -> str:
    """QA 2단계. 회사 기사에서 찾은 본문 조각으로 답한다. "답 없음"이거나 본문에 없는 답이면 NOT_FOUND_MESSAGE."""
    text = _article_text(context)
    answer = generate_answer(text, question)
    return answer if _usable_answer(answer, text) else NOT_FOUND_MESSAGE
