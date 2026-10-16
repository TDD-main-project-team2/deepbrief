"""
1. decide_task: 질문이 "회사 기사 통계"인지 "기사 내용 질문"인지 코드 규칙으로 가른다 (모델 호출 없음)
2. query_company_data: 회사(조직) 기사 수·최근 목록·분야별 개수를 DB에서 읽어 문장으로 돌려준다 (모델 호출 없음)
3. search_web: Tavily로 웹을 검색한다. 키가 없으면 키 없이(keyless) 요청한다. 질문만 보내고 기사 본문은 보내지 않는다
4. format_web_context: 웹 결과를 답변용 문맥으로 만든다
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
from backend.models.user import User
from backend.models.user_article import UserArticle

load_dotenv()
logger = logging.getLogger(__name__)

# 한국 시간. 서머타임이 없어 +09:00 고정이 정확하다 (ZoneInfo는 윈도우에서 tzdata 패키지가 필요)
KST = timezone(timedelta(hours=9))

# 기사 분야. 다른 모듈과 묶이지 않도록 여기에 따로 둔다 (model_service.ARTICLE_CATEGORIES와 같은 값)
CATEGORIES = ("정치", "경제", "사회", "문화", "IT", "과학", "세계", "엔터테인먼트", "스포츠")
UNCATEGORIZED = "미분류"

# 질문 분기 규칙. 비교는 공백을 지운 질문으로 한다
CURRENT_ARTICLE_WORDS = ("이기사", "현재기사", "본기사", "해당기사")
COMPANY_WORDS = ("회사", "우리", "조직", "전체")
ARTICLE_WORD = "기사"
AGGREGATE_WORDS = ("몇개", "몇건", "개수", "건수", "목록", "리스트", "최근기사", "최근에올라온", "통계", "분야별", "카테고리별")
LIST_WORDS = ("목록", "리스트", "최근기사", "최근에올라온", "어떤기사")
BY_CATEGORY_WORDS = ("분야별", "카테고리별")

RECENT_LIMIT = 5

ORG_NOT_FOUND = "조직 정보를 찾을 수 없습니다."
COMPANY_DATA_ERROR = "회사 기사 정보를 불러오지 못했습니다."

# Tavily 웹 검색 (무료 플랜, basic = 1크레딧). 키가 없으면 keyless 모드 (무료, 사용량 제한 있음)
TAVILY_URL = "https://api.tavily.com/search"
WEB_MAX_RESULTS = 5
WEB_TIMEOUT = 10.0
WEB_CONTENT_MAX = 500


def _compact(text: str) -> str:
    """공백을 모두 지운다. 띄어쓰기 차이("몇 개"/"몇개")를 무시하려고 쓴다."""
    return re.sub(r"\s+", "", text)


# ── 질문 해석 ────────────────────────────────────────

def decide_task(question: str) -> str:
    """
    "company_data": 회사 기사 통계 질문 (회사·우리·조직·전체 + "기사" + 집계어가 모두 있음)
    "article": 그 밖의 모든 질문. "이 기사", "현재 기사"가 있으면 무조건 article
    """
    text = _compact(question)
    if any(word in text for word in CURRENT_ARTICLE_WORDS):
        return "article"
    if (any(word in text for word in COMPANY_WORDS) and ARTICLE_WORD in text
            and any(word in text for word in AGGREGATE_WORDS)):
        return "company_data"
    return "article"


def parse_period(question: str, now: datetime | None = None) -> tuple[datetime, datetime, str] | None:
    """
    질문의 기간 표현을 [시작, 끝) 구간으로 바꾼다 (한국 시간). 없으면 None (전체 기간).
    오늘, 어제, 이번 주, 지난주, 이번 달, 지난달, 올해, 최근 N일. 주는 월요일부터 시작한다.
    """
    text = _compact(question)
    now = (now or datetime.now(KST)).astimezone(KST)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    this_week = today - timedelta(days=today.weekday())
    this_month = today.replace(day=1)
    next_month = (this_month + timedelta(days=32)).replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)

    recent = re.search(r"최근(\d+)일", text)
    if recent:
        days = max(int(recent.group(1)), 1)
        return today - timedelta(days=days - 1), tomorrow, f"최근 {days}일"
    if "오늘" in text:
        return today, tomorrow, "오늘"
    if "어제" in text:
        return today - timedelta(days=1), today, "어제"
    if "지난주" in text or "저번주" in text:
        return this_week - timedelta(days=7), this_week, "지난주"
    if "이번주" in text or "금주" in text:
        return this_week, this_week + timedelta(days=7), "이번 주"
    if "지난달" in text or "저번달" in text:
        return last_month, this_month, "지난달"
    if "이번달" in text:
        return this_month, next_month, "이번 달"
    if "올해" in text or "금년" in text:
        this_year = today.replace(month=1, day=1)
        return this_year, this_year.replace(year=this_year.year + 1), "올해"
    return None


def parse_category(question: str) -> str | None:
    """질문에 들어 있는 기사 분야. 없으면 None (전체 분야)."""
    for category in CATEGORIES:
        if category == "IT":
            if re.search(r"(?<![A-Za-z])IT(?![A-Za-z])", question, re.IGNORECASE):
                return category
        elif category in question:
            return category
    return None


# ── DB 조회 (읽기 전용, SQL은 이 아래 함수들에만 있다) ─────

def _article_date():
    """기간 기준 날짜: 작성일, 없으면 업로드 시각."""
    return func.coalesce(Article.published_at, Article.created_at)


def _organization_articles(query, organization_id: int, period, category: str | None):
    """조직 사용자가 가진 기사로 거르고, 기간·분야 조건을 붙인다."""
    query = (
        query.join(UserArticle, UserArticle.article_id == Article.id)
        .join(User, User.id == UserArticle.user_id)
        .filter(User.organization_id == organization_id)
    )
    if period is not None:
        start, end, _ = period
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


def _count_articles(session, organization_id: int, period, category: str | None) -> int:
    """조직 기사 수. 같은 기사를 조직 안의 여러 명이 가져도 한 번만 센다."""
    query = session.query(func.count(distinct(Article.id)))
    return _organization_articles(query, organization_id, period, category).scalar() or 0


def _list_recent_articles(session, organization_id: int, period, category: str | None, limit: int = RECENT_LIMIT):
    """조직의 최근 기사 (제목, 날짜). 최신순."""
    query = session.query(Article.id, Article.title, _article_date().label("date"))
    query = _organization_articles(query, organization_id, period, category).distinct()
    return query.order_by(desc("date"), desc(Article.id)).limit(limit).all()


def _count_articles_by_category(session, organization_id: int, period) -> list[tuple[str, int]]:
    """조직 기사의 분야별 개수. 분야가 없으면 "미분류". 많은 순."""
    query = session.query(Article.category, func.count(distinct(Article.id)))
    rows = _organization_articles(query, organization_id, period, None).group_by(Article.category).all()
    counts = [(category or UNCATEGORIZED, count) for category, count in rows]
    return sorted(counts, key=lambda row: (-row[1], row[0]))


# ── 회사 기사 통계 ───────────────────────────────────

def _format_date(value) -> str:
    if value is None:
        return "날짜 없음"
    if isinstance(value, str):          # SQLite 등에서 문자열로 올 때
        return value[:10]
    if value.tzinfo is not None:
        value = value.astimezone(KST)
    return value.strftime("%Y-%m-%d")


def query_company_data(question: str, article_id: int) -> str:
    """
    회사 기사 통계 질문에 답한다 (모델 호출 없음).
    "목록·최근 기사" → 최근 목록, "분야별" → 분야별 개수, 그 밖 → 기사 수.
    답변에는 적용한 조건(기간, 분야)을 항상 적는다.
    """
    text = _compact(question)
    period = parse_period(question)
    category = parse_category(question)
    period_label = period[2] if period else "전체 기간"
    category_label = category or "전체 분야"

    try:
        with SessionLocal() as session:
            organization_id = _find_organization_id(session, article_id)
            if organization_id is None:
                return ORG_NOT_FOUND

            if any(word in text for word in BY_CATEGORY_WORDS):
                counts = _count_articles_by_category(session, organization_id, period)
                total = sum(count for _, count in counts)
                if total == 0:
                    return f"{period_label} 기준 회사 기사가 없습니다."
                lines = [f"{period_label} 기준 회사 기사 분야별 개수입니다. (총 {total}건)"]
                lines += [f"- {name}: {count}건" for name, count in counts]
                return "\n".join(lines)

            if any(word in text for word in LIST_WORDS):
                rows = _list_recent_articles(session, organization_id, period, category)
                if not rows:
                    return f"{period_label}, {category_label} 기준 회사 기사가 없습니다."
                lines = [f"{period_label}, {category_label} 기준 최근 회사 기사 {len(rows)}건입니다."]
                lines += [f"{index}. {row.title} ({_format_date(row.date)})" for index, row in enumerate(rows, 1)]
                return "\n".join(lines)

            count = _count_articles(session, organization_id, period, category)
            return f"{period_label}, {category_label} 기준 회사 기사는 {count}건입니다."
    except Exception:
        logger.exception("회사 기사 통계 조회에 실패했습니다.")      # 질문 원문은 로그에 남기지 않는다
        return COMPANY_DATA_ERROR


# ── 웹 검색 (Tavily) ─────────────────────────────────

def search_web(query: str) -> list[dict]:
    """
    Tavily 웹 검색. [{"title", "url", "content"(500자까지)}], 최대 5개.
    .env에 TAVILY_API_KEY가 있으면 그 키로, 없으면 keyless 모드로 요청한다.
    실패하면(무료 한도 초과 432, keyless 사용량 제한 포함) 빈 목록. 질문만 보내고 기사 본문은 보내지 않는다.
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


def format_web_context(results: list[dict]) -> str:
    """웹 결과를 답변 생성용 문맥으로 잇는다 (제목 + 내용)."""
    return "\n\n".join(f"{result['title']}\n{result['content']}" for result in results)
