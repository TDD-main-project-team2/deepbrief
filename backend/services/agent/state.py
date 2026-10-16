from typing import Literal, TypedDict


class AgentState(TypedDict):
    question: str
    article_id: int

    conversation_history: list
    task: Literal["article", "company_data"]
    retrieval_scope: Literal["current_article", "organization", "web"]
    context: str
    answer: str 
