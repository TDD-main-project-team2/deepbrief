from langgraph.graph import StateGraph, START, END

from .state import AgentState
from . import nodes


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("retrieve_article_context", nodes.retrieve_article_context)
    graph.add_node("decide_retrieval_scope", nodes.decide_retrieval_scope)
    graph.add_node("retrieve_additional_context", nodes.retrieve_additional_context)
    graph.add_node("answer_question", nodes.answer_question)

    graph.add_edge(START, "retrieve_article_context")
    graph.add_edge("retrieve_article_context", "decide_retrieval_scope")
    graph.add_edge("decide_retrieval_scope", "retrieve_additional_context")
    graph.add_edge("retrieve_additional_context", "answer_question")
    graph.add_edge("answer_question", END)

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
        "context": "",
        "retrieval_scope": "",
        "answer": "",
    }

    return await agent.ainvoke(initial_state)