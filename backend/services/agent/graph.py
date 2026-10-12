from langgraph.graph import StateGraph, START, END

from .state import AgentState
from . import nodes


def build_graph():
    graph = StateGraph(AgentState)
    intent = state["intent"]

    graph.add_node("classify_request", nodes.classify_request)

    #qa 
    if intent : "summarize":
    graph.add_node("summarize_article", nodes.summarize_article)
    graph.add_node("search_news", nodes.search_news)
    graph.add_node("generate_answer", nodes.generate_answer)

    graph.add_edge(START, "classify_request")
    graph.add_edge("generate_answer", END)

    return graph.compile()

agent = build_graph()

async def run_agent(
    question: str,
    intent: str,
    article_id: str | None = None,
    conversation_history: list | None = None,
):
    conversation_history = (conversation_history or [])[-10:]

    initial_state = {
        "question": question,
        "intent": intent,
        "article_id": article_id,
        "conversation_history": conversation_history or [],
        "category": "",
        "summary": "",
        "retrieved_articles": [],
        "search_results": [],
        "answer": "",
    }

    return await agent.ainvoke(initial_state)