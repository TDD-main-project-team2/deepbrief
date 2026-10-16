from langgraph.graph import StateGraph, START, END

from .state import AgentState
from . import nodes
from backend.services.ai import model_service


def route_task(state: AgentState):
    return state["task"]

def route_after_scope(state: AgentState):
    return END if state["retrieval_scope"] == "current_article" else "retrieve_additional_context"

def route_after_answer(state: AgentState):
    not_found = state["answer"] == model_service.NOT_FOUND_MESSAGE
    return "search_web" if state["retrieval_scope"] == "organization" and not_found else END


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("decide_task", nodes.decide_task)
    graph.add_node("query_company_data", nodes.query_company_data)
    graph.add_node("retrieve_article_context", nodes.retrieve_article_context)
    graph.add_node("decide_retrieval_scope", nodes.decide_retrieval_scope)
    graph.add_node("retrieve_additional_context", nodes.retrieve_additional_context)
    graph.add_node("search_web", nodes.search_web)
    graph.add_node("answer_question", nodes.answer_question)

    graph.add_edge(START, "decide_task")
    graph.add_conditional_edges("decide_task", route_task, {"company_data": "query_company_data", "article": "retrieve_article_context"})
    graph.add_edge("query_company_data", END)
    graph.add_edge("retrieve_article_context", "decide_retrieval_scope")
    graph.add_conditional_edges("decide_retrieval_scope", route_after_scope)
    graph.add_edge("retrieve_additional_context", "answer_question")
    graph.add_conditional_edges("answer_question", route_after_answer)
    graph.add_edge("search_web", "answer_question")

    return graph.compile()

agent = build_graph()

async def run_agent(
    question: str,
    article_id: int,
    conversation_history: list | None = None,
):
    conversation_history = (conversation_history or [])[-10:]

    initial_state = {
        "question": question,
        "article_id": article_id,
        "conversation_history": conversation_history or [],
        "task": "article",
        "context": "",
        "retrieval_scope": "current_article",
        "answer": "",
    }

    return await agent.ainvoke(initial_state)