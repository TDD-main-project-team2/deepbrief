from agent.state import AgentState
from . import tools
from services.ai import model_service
from services.rag import rag_service
from services.resources import article_service

def retrieve_article_context(state: AgentState):
    chunks = rag_service.retrieve_article_chunks(state["question"], state["article_id"])
    context = rag_service.build_context(chunks)
    return {"context": context}

def decide_retrieval_scope(state: AgentState):
    scope = model_service.classify_retrieval_scope(state["question"], state["context"])
    return {"retrieval_scope": scope}

def retrieve_additional_context(state: AgentState):
    if state["retrieval_scope"] == "current_article":
        return {}

    if state["retrieval_scope"] == "organization":
        chunks = rag_service.retrieve_org_chunks(state["question"], state["article_id"])
        context = rag_service.build_context(chunks)
        return {"context": context}

    raise ValueError(f"Unknown retrieval scope: {state['retrieval_scope']}")

def answer_question(state: AgentState):
    answer = model_service.generate_answer(state["question"], state["context"], state["conversation_history"])
    return {
        "answer": answer
    }