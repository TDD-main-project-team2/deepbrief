import logging

from .state import AgentState
from . import tools
from backend.services.ai import model_service
from backend.services.rag import rag_service

logger = logging.getLogger(__name__)

def decide_task(state: AgentState):
    return {"task": tools.decide_task(state["question"])}

def query_company_data(state: AgentState):
    return {"answer": tools.query_company_data(state["question"], state["article_id"])}

def retrieve_article_context(state: AgentState):
    chunks = rag_service.retrieve_similar_article_chunks(state["question"], state["article_id"])
    context = rag_service.build_context(chunks)
    return {"context": context}

def decide_retrieval_scope(state: AgentState):
    result = model_service.decide_answer_source(state["context"], state["question"])
    if result["source"] == "current_article":
        return {"retrieval_scope": "current_article", "answer": result["answer"]}
    return {"retrieval_scope": "organization"}

def retrieve_additional_context(state: AgentState):
    if state["retrieval_scope"] == "current_article":
        return {}

    if state["retrieval_scope"] == "organization":
        try:
            chunks = rag_service.retrieve_org_chunks(state["question"], state["article_id"])
        except Exception as error:       # 조직 없음 등 → 문맥 없이 넘겨 웹 검색으로
            logger.warning("회사 기사 검색 실패: %s", type(error).__name__)
            return {"context": ""}
        context = rag_service.build_context(chunks)
        return {"context": context}

    raise ValueError(f"Unknown retrieval scope: {state['retrieval_scope']}")

def search_web(state: AgentState):
    results = tools.search_web(state["question"])
    return {"retrieval_scope": "web", "context": tools.format_web_context(results)}

def answer_question(state: AgentState):
    if not state["context"].strip():
        return {"answer": model_service.NOT_FOUND_MESSAGE}
    answer = model_service.generate_organization_answer(state["context"], state["question"])
    return {
        "answer": answer
    }
