from agent.state import AgentState
from . import tools
from services.ai import model_service

def process_question(state: AgentState):
    question = state["question"].strip()
    return {
        "question": question
    }

def classify_article(state: AgentState):
    category = model_service.classify_article(state["category"])
    return {
        "category": category
    }

def generate_answer(state: AgentState):
    answer = model_service.answer_question(state["question"], state["conversation_history"], state["article_id"])
    return {
        "answer": answer
    }

def summarize_article(state: AgentState):
    summary = model_service.summarize_article(state["article_id"])
    return {
        "summary": summary
    }

def search_news(state: AgentState):
    ...

def analyze_trend(state: AgentState):
    ...

def recommend_articles(state: AgentState):
    ...