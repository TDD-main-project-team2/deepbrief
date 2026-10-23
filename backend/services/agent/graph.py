from langgraph.graph import StateGraph, START, END
from sqlalchemy.orm import Session
from .state import AgentState
from . import nodes


def build_graph(db: Session):
    graph = StateGraph(AgentState)

    graph.add_node("decide_question_type", nodes.decide_question_type)
    graph.add_node("feature_node", lambda state: nodes.feature_node(state, db))
    graph.add_node("retrieve_article_context", nodes.retrieve_article_context)
    graph.add_node("decide_retrieval_scope", nodes.decide_retrieval_scope)
    graph.add_node("retrieve_additional_context", nodes.retrieve_additional_context)
    graph.add_node("answer_question", nodes.answer_question)

    graph.add_edge(START, "decide_question_type")
    graph.add_conditional_edges(
        "decide_question_type",
        route_question,
        {
            "feature": "feature_node",
            "qa": "retrieve_article_context",
        },
    )
    graph.add_edge("feature_node", "answer_question")
    graph.add_edge("retrieve_article_context", "decide_retrieval_scope")
    graph.add_edge("decide_retrieval_scope", "retrieve_additional_context")
    graph.add_edge("retrieve_additional_context", "answer_question")
    graph.add_edge("answer_question", END)

    return graph.compile()


async def run_agent(
    question: str,
    article_id: int,
    user_id: int,
    db: Session,
    conversation_history: list | None = None,
):
    conversation_history = (conversation_history or [])[-10:]
    agent = build_graph(db)

    initial_state = {
        "question": question,
        "question_type": "",
        "article_id": article_id,
        "user_id": user_id,
        "conversation_history": conversation_history or [],
        "context": "",
        "retrieval_scope": "",
        "answer": "",
    }

    return await agent.ainvoke(initial_state)


def route_question(state: AgentState):
    if state["question_type"] in {"title", "keyword", "idea", "headline", "dupe", "eval", "edit"}:
        return "feature"
    return "qa"