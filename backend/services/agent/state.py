from typing import TypedDict


class AgentState(TypedDict):
    question: str
    question_type: str
    article_id: int
    user_id: int

    conversation_history: list
    retrieval_scope: str
    context: str
    answer: str 
