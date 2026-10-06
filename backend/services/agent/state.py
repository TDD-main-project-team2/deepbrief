from typing import TypedDict


class AgentState(TypedDict):
    intent: str
    question: str
    answer: str
