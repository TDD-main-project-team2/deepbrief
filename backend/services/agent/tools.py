"""
Tools

노드가 부르는 입구 함수는 두 개다.
1. search_web: Tavily로 웹을 검색해 답변용 문맥을 돌려준다. 질문만 보내고 기사 본문은 보내지 않는다
2. query_company_data: 사내 데이터 조회. LLM(model_service.select_company_data_tool)이
   조회 도구 8개 중 하나와 인자를 고르고, 코드가 확인·교정한 뒤 DB에서 읽어 문장으로 돌려준다
   (도구 목록과 프롬프트는 model_service.COMPANY_DATA_TOOLS에 있다)

조회 도구는 두 겹이다. 안쪽 `_조회` 함수는 SQL만, 바깥 도구 함수는 인자 확인과 문장 만들기를 맡는다.
조직과 DB 세션은 코드가 넣고 LLM에게는 보이지 않는다.
"""
import logging
import os
import re
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv
from sqlalchemy import desc, distinct, func
from sqlalchemy.exc import MultipleResultsFound

from backend.database.rdb.rdb import SessionLocal
from backend.models.article import Article
from backend.models.guideline import Guideline
from backend.models.template import Template
from backend.models.user import User
from backend.models.user_article import UserArticle
from backend.services.ai import model_service

load_dotenv()
logger = logging.getLogger(__name__)

# 한국 시간
KST = timezone(timedelta(hours=9))

# 기사 분야
CATEGORIES = ("정치", "경제", "사회", "문화", "IT", "과학", "세계", "엔터테인먼트", "스포츠")
UNCATEGORIZED = "미분류"

# 기간
PERIODS = ("today", "yesterday", "this_week", "last_week", "this_month", "last_month",
           "last_7_days", "last_30_days", "this_year", "all")
PERIOD_LABELS = {
    "today": "오늘", "yesterday": "어제", "this_week": "이번 주", "last_week": "지난주",
    "this_month": "이번 달", "last_month": "지난달", "last_7_days": "최근 7일",
    "last_30_days": "최근 30일", "this_year": "올해", "all": "전체 기간",
}

RECENT_LIMIT = 5
LIST_LIMIT = 20
NAME_MAX = 50

# Tavily 웹 검색
# 키가 없으면 keyless 모드
TAVILY_URL = "https://api.tavily.com/search"
WEB_MAX_RESULTS = 5
WEB_TIMEOUT = 10.0
WEB_CONTENT_MAX = 500

# LLM 출력을 읽을 수 없을 때 쓰는 키워드 규칙 (비교는 공백을 지운 질문으로 한다)
LIST_WORDS = ("목록", "리스트", "최근기사", "최근에올라온", "어떤기사")
BY_CATEGORY_WORDS = ("분야별", "카테고리별")
COUNT_WORDS = ("몇개", "몇건", "개수", "건수")
DEPARTMENT = re.compile(r"(%s)부" % "|".join(CATEGORIES))   # '정치부' 같은 부서 이름


def _compact(text: str) -> str:
    """공백을 모두 지운다. 띄어쓰기 차이("몇 개"/"몇개")를 무시하려고 쓴다."""
    return re.sub(r"\s+", "", text)


# ── 기간·분야 ─────────────────────────────────────────

def _period_range(period: str, now: datetime | None = None) -> tuple[datetime, datetime] | None:
    """기간 값을 [시작, 끝) 구간으로 바꾼다 (한국 시간). "all"이면 None. 주는 월요일부터 시작한다."""
    now = (now or datetime.now(KST)).astimezone(KST)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    this_week = today - timedelta(days=today.weekday())
    this_month = today.replace(day=1)
    next_month = (this_month + timedelta(days=32)).replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)
    this_year = today.replace(month=1, day=1)
    ranges = {
        "today": (today, tomorrow),
        "yesterday": (today - timedelta(days=1), today),
        "this_week": (this_week, this_week + timedelta(days=7)),
        "last_week": (this_week - timedelta(days=7), this_week),
        "this_month": (this_month, next_month),
        "last_month": (last_month, this_month),
        "last_7_days": (today - timedelta(days=6), tomorrow),
        "last_30_days": (today - timedelta(days=29), tomorrow),
        "this_year": (this_year, this_year.replace(year=this_year.year + 1)),
    }
    return ranges.get(period)


def _period_from_question(question: str) -> str:
    """키워드 규칙용. 질문의 기간 표현을 기간 값으로 바꾼다. 없으면 "all"."""
    text = _compact(question)
    rules = (("최근7일", "last_7_days"), ("최근일주일", "last_7_days"), ("최근30일", "last_30_days"),
             ("최근한달", "last_30_days"), ("오늘", "today"), ("어제", "yesterday"),
             ("지난주", "last_week"), ("저번주", "last_week"), ("이번주", "this_week"), ("금주", "this_week"),
             ("지난달", "last_month"), ("저번달", "last_month"), ("이번달", "this_month"),
             ("올해", "this_year"), ("금년", "this_year"))
    for word, period in rules:
        if word in text:
            return period
    return "all"


def _category_from_question(question: str) -> str | None:
    """키워드 규칙용. 질문에 들어 있는 기사 분야. 없으면 None (전체 분야)."""
    for category in CATEGORIES:
        if category == "IT":
            if re.search(r"(?<![A-Za-z])IT(?![A-Za-z])", question, re.IGNORECASE):
                return category
        elif category in question:
            return category
    return None


# ── DB 조회 ─────────

def _article_date():
    """기간 기준 날짜: 작성일, 없으면 업로드 시각."""
    return func.coalesce(Article.published_at, Article.created_at)


def _organization_articles(query, organization_id: int, period: str, category: str | None = None):
    """조직 사용자가 가진 기사로 거르고, 기간·분야 조건을 붙인다."""
    query = (
        query.join(UserArticle, UserArticle.article_id == Article.id)
        .join(User, User.id == UserArticle.user_id)
        .filter(User.organization_id == organization_id)
    )
    period_range = _period_range(period)
    if period_range is not None:
        start, end = period_range
        query = query.filter(_article_date() >= start, _article_date() < end)
    if category is not None:
        query = query.filter(Article.category == category)
    return query


def _find_organization_id(session, article_id: int) -> int | None:
    """기사를 가진 사용자의 조직 (vector_db.search_organization_chunks와 같은 조인). 없거나 여러 개면 None."""
    try:
        return (
            session.query(User.organization_id)
            .join(UserArticle, UserArticle.user_id == User.id)
            .filter(UserArticle.article_id == article_id)
            .distinct()
            .scalar()
        )
    except MultipleResultsFound:
        logger.warning("기사 %s에 연결된 조직이 여러 개입니다.", article_id)
        return None


def _count_articles(session, organization_id, period, category=None) -> int:
    """조직 기사 수. 같은 기사를 조직 안의 여러 명이 가져도 한 번만 센다."""
    query = session.query(func.count(distinct(Article.id)))
    return _organization_articles(query, organization_id, period, category).scalar() or 0


def _list_recent_articles(session, organization_id, period, category=None, limit=RECENT_LIMIT):
    """조직의 최근 기사 (제목, 날짜). 최신순."""
    query = session.query(Article.id, Article.title, _article_date().label("date"))
    query = _organization_articles(query, organization_id, period, category).distinct()
    return query.order_by(desc("date"), desc(Article.id)).limit(limit).all()


def _count_articles_by_category(session, organization_id, period) -> list[tuple[str, int]]:
    """조직 기사의 분야별 개수. 분야가 없으면 "미분류". 많은 순."""
    query = session.query(Article.category, func.count(distinct(Article.id)))
    rows = _organization_articles(query, organization_id, period).group_by(Article.category).all()
    counts = [(category or UNCATEGORIZED, count) for category, count in rows]
    return sorted(counts, key=lambda row: (-row[1], row[0]))


def _like(value: str) -> str:
    """LIKE 검색어. %와 _를 글자 그대로 찾도록 감싼다."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _count_articles_by_author(session, organization_id, period, author) -> int:
    """기자 이름이 들어간 조직 기사 수 (기자가 여러 명인 기사 포함)."""
    query = session.query(func.count(distinct(Article.id))).filter(Article.author.like(_like(author), escape="\\"))
    return _organization_articles(query, organization_id, period).scalar() or 0


def _count_articles_by_media(session, organization_id, period, media) -> int:
    """언론사 이름이 들어간 조직 기사 수."""
    query = session.query(func.count(distinct(Article.id))).filter(Article.media.like(_like(media), escape="\\"))
    return _organization_articles(query, organization_id, period).scalar() or 0


def _list_templates(session, organization_id) -> list[str]:
    """조직의 기사 템플릿 제목."""
    rows = (session.query(Template.title).filter(Template.organization_id == organization_id)
            .order_by(Template.id).limit(LIST_LIMIT).all())
    return [row.title for row in rows]


def _list_guidelines(session, organization_id) -> list[str]:
    """조직의 작성 지침 제목."""
    rows = (session.query(Guideline.title).filter(Guideline.organization_id == organization_id)
            .order_by(Guideline.id).limit(LIST_LIMIT).all())
    return [row.title for row in rows]


def _count_members(session, organization_id) -> int:
    """조직 구성원 수."""
    return session.query(func.count(User.id)).filter(User.organization_id == organization_id).scalar() or 0


# ── 사내 데이터 조회 도구 (LLM이 고르는 것, query_company_data 안에서만 부름) ──
# 각 도구는 (session, organization_id, LLM이 고른 인자)를 받아 답변용 문장을 돌려준다

def _format_date(value) -> str:
    if value is None:
        return "날짜 없음"
    if isinstance(value, str):          # SQLite 등에서 문자열로 올 때
        return value[:10]
    if value.tzinfo is not None:
        value = value.astimezone(KST)
    return value.strftime("%Y-%m-%d")


def _tool_count_articles(session, organization_id, period="all", category=None) -> str:
    count = _count_articles(session, organization_id, period, category)
    return f"{PERIOD_LABELS[period]}, {category or '전체 분야'} 기준 회사 기사는 {count}건입니다."


def _tool_list_recent_articles(session, organization_id, period="all", category=None) -> str:
    rows = _list_recent_articles(session, organization_id, period, category)
    label = f"{PERIOD_LABELS[period]}, {category or '전체 분야'} 기준"
    if not rows:
        return f"{label} 회사 기사가 없습니다."
    lines = [f"{label} 최근 회사 기사 {len(rows)}건입니다."]
    lines += [f"{index}. {row.title} ({_format_date(row.date)})" for index, row in enumerate(rows, 1)]
    return "\n".join(lines)


def _tool_count_articles_by_category(session, organization_id, period="all") -> str:
    counts = _count_articles_by_category(session, organization_id, period)
    total = sum(count for _, count in counts)
    if total == 0:
        return f"{PERIOD_LABELS[period]} 기준 회사 기사가 없습니다."
    lines = [f"{PERIOD_LABELS[period]} 기준 회사 기사 분야별 개수입니다. (총 {total}건)"]
    lines += [f"- {name}: {count}건" for name, count in counts]
    return "\n".join(lines)


def _tool_count_articles_by_author(session, organization_id, author, period="all") -> str:
    count = _count_articles_by_author(session, organization_id, period, author)
    return f"{PERIOD_LABELS[period]} 기준 {author} 기자의 회사 기사는 {count}건입니다."


def _tool_count_articles_by_media(session, organization_id, media, period="all") -> str:
    count = _count_articles_by_media(session, organization_id, period, media)
    return f"{PERIOD_LABELS[period]} 기준 {media} 회사 기사는 {count}건입니다."


def _tool_list_templates(session, organization_id) -> str:
    titles = _list_templates(session, organization_id)
    if not titles:
        return "회사에 등록된 기사 템플릿이 없습니다."
    return "\n".join([f"회사 기사 템플릿 {len(titles)}개입니다."] + [f"{i}. {t}" for i, t in enumerate(titles, 1)])


def _tool_list_guidelines(session, organization_id) -> str:
    titles = _list_guidelines(session, organization_id)
    if not titles:
        return "회사에 등록된 작성 지침이 없습니다."
    return "\n".join([f"회사 작성 지침 {len(titles)}개입니다."] + [f"{i}. {t}" for i, t in enumerate(titles, 1)])


def _tool_count_members(session, organization_id) -> str:
    return f"회사 구성원은 {_count_members(session, organization_id)}명입니다."


_COMPANY_DATA_FUNCTIONS = {
    "count_articles": _tool_count_articles,
    "list_recent_articles": _tool_list_recent_articles,
    "count_articles_by_category": _tool_count_articles_by_category,
    "count_articles_by_author": _tool_count_articles_by_author,
    "count_articles_by_media": _tool_count_articles_by_media,
    "list_templates": _tool_list_templates,
    "list_guidelines": _tool_list_guidelines,
    "count_members": _tool_count_members,
}


def _check_call(call: dict | None, question: str):
    """
    LLM이 고른 호출을 확인하고, 질문과 어긋나면 고친다. (도구 함수, 인자) 또는 쓸 수 없으면 None.
    - 거부: 없는 도구, 정의에 없는 인자, 정해진 값 밖의 기간·분야, 질문에 없는 기자·언론사 이름(지어낸 이름)
    """
    if call is None or call["name"] not in _COMPANY_DATA_FUNCTIONS:
        return None
    name = call["name"]
    spec = next(t["function"]["parameters"] for t in model_service.COMPANY_DATA_TOOLS if t["function"]["name"] == name)
    arguments = {key: value for key, value in call["arguments"].items() if value not in (None, "")}
    text = _compact(question)

    for key in ("author", "media"):
        department = DEPARTMENT.fullmatch(str(arguments.get(key, "")).strip())
        if department:
            name, arguments = "count_articles", {"period": arguments.get("period", "all"), "category": department.group(1)}
            spec = next(t["function"]["parameters"] for t in model_service.COMPANY_DATA_TOOLS
                        if t["function"]["name"] == name)
            break
    if name == "count_articles_by_category" and not any(word in text for word in BY_CATEGORY_WORDS):
        name = "count_articles"
        spec = next(t["function"]["parameters"] for t in model_service.COMPANY_DATA_TOOLS if t["function"]["name"] == name)
    if name == "list_recent_articles" and any(word in text for word in COUNT_WORDS):
        name = "count_articles"

    if set(arguments) - set(spec["properties"]) or set(spec["required"]) - set(arguments):
        return None
    if "period" in spec["properties"]:
        arguments.setdefault("period", "all")
        if arguments["period"] not in PERIODS:
            return None
    if arguments.get("category") is not None and arguments["category"] not in CATEGORIES:
        return None
    for key in ("author", "media"):
        if key in arguments:
            value = str(arguments[key]).strip()
            if not value or len(value) > NAME_MAX or _compact(value) not in text:
                return None
            arguments[key] = value
    return _COMPANY_DATA_FUNCTIONS[name], arguments


def _fallback_call(question: str):
    """LLM 출력을 쓸 수 없을 때의 키워드 규칙: 분야별 / 최근 목록 / 기사 수."""
    text = _compact(question)
    period = _period_from_question(question)
    if any(word in text for word in BY_CATEGORY_WORDS):
        return _tool_count_articles_by_category, {"period": period}
    category = _category_from_question(question)
    if any(word in text for word in LIST_WORDS):
        return _tool_list_recent_articles, {"period": period, "category": category}
    return _tool_count_articles, {"period": period, "category": category}


def query_company_data(question: str, article_id: int) -> str:
    """
    사내 데이터 조회 (노드가 부르는 입구). LLM이 조회 도구와 인자를 고르고, 코드가 확인한 뒤 실행한다.
    LLM 출력을 쓸 수 없으면 키워드 규칙으로 대신 고른다. 조직이 없거나 조회에 실패하면 "".
    """
    try:
        with SessionLocal() as session:
            organization_id = _find_organization_id(session, article_id)
            if organization_id is None:
                return ""
            selected = _check_call(model_service.select_company_data_tool(question), question)
            if selected is None:
                logger.info("사내 데이터 조회 도구 선택을 읽을 수 없어 키워드 규칙을 씁니다.")
                selected = _fallback_call(question)
            function, arguments = selected
            return function(session, organization_id, **arguments)
    except Exception:
        logger.exception("사내 데이터 조회에 실패했습니다.")
        return ""


# ── 웹 검색 (Tavily) ─────────────────────────────────

def _search_web_results(query: str) -> list[dict]:
    """
    Tavily 웹 검색. [{"title", "url", "content"(500자까지)}], 최대 5개.
    .env에 TAVILY_API_KEY가 있으면 그 키로, 없으면 keyless 모드로 요청한다.
    실패하면(무료 한도 초과 432, keyless 사용량 제한 등) 빈 목록. 질문만 보내고 기사 본문은 보내지 않는다.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key:
        headers = {"Authorization": f"Bearer {api_key}"}
    else:
        headers = {"X-Tavily-Access-Mode": "keyless"}

    try:
        response = httpx.post(
            TAVILY_URL,
            headers=headers,
            json={
                "query": query,
                "search_depth": "basic",
                "topic": "general",
                "max_results": WEB_MAX_RESULTS,
            },
            timeout=WEB_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as error:
        logger.warning("웹 검색 실패: HTTP %s", error.response.status_code)
        return []
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("웹 검색 실패: %s", type(error).__name__)
        return []

    results = []
    for item in data.get("results") or []:
        url = (item.get("url") or "").strip()
        content = (item.get("content") or "").strip()
        if url and content:
            results.append({
                "title": (item.get("title") or url).strip(),
                "url": url,
                "content": content[:WEB_CONTENT_MAX],
            })
    return results[:WEB_MAX_RESULTS]


def search_web(query: str) -> str:
    """
    웹 검색 (노드가 부르는 입구).
    결과를 답변용 문맥(제목 + 내용)으로 잇는다. 실패하면 ""
    """
    results = _search_web_results(query)
    return "\n\n".join(f"{result['title']}\n{result['content']}" for result in results)
