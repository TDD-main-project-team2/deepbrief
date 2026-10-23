from .state import AgentState
from . import tools
from backend.services.ai import model_service
from backend.services.rag import rag_service
from backend.services.features import review_service, recommend_service, edit_service

def decide_question_type(state: AgentState):
    type = model_service.classify_question_type(state["question"])
    return {"question_type": type}

def feature_node(state: AgentState):
    if state["question_type"] == "title":
        answer = model_service.generate_title
    elif state["question_type"] == "keyword":
        answer = model_service.generate_keyword_tags
    elif state["question_type"] == "idea":
        answer = model_service.generate_article_ideas
    elif state["question_type"] == "headline":
        answer = model_service.generate_summary
    elif state["question_type"] == "dupe":
        answer = review_service.check_duplicates_logic(state["article_id"])
    elif state["question_type"] == "eval":
        answer = model_service.generate_article_evaluation
    
    return {
        "answer": answer
    }

def retrieve_article_context(state: AgentState):
    chunks = rag_service.retrieve_similar_article_chunks(state["question"], state["article_id"])
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

    if state["retrieval_scope"] == "web":
        return {"context": tools.search_web(state["question"])}

    if state["retrieval_scope"] == "company_data":
        return {"context": tools.query_company_data(state["question"], state["article_id"])}

    raise ValueError(f"Unknown retrieval scope: {state['retrieval_scope']}")

def answer_question(state: AgentState):
    if not state["context"].strip():
        return {"answer": model_service.NOT_FOUND_MESSAGE}
    answer = model_service.generate_answer(state["context"], state["question"])
    return {
        "answer": answer
    }
