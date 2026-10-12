from typing import TypedDict


class AgentState(TypedDict):
    intent: str
    question: str
    category: str

    summary: str
    answer: str

    article_id: int

    conversation_history: list
    retrieved_articles: list
    search_results: list