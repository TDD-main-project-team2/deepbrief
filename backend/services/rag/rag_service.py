from backend.database.vector.vector_db import VectorDB
from backend.services.ai.embedding_service import embed_query
from backend.models.article_chunk import ArticleChunk

def retrieve_similar_article_chunks(question: str, article_id: int, top_k: int = 5) -> list[ArticleChunk]:
    embedding = embed_query(question)
    return VectorDB.search_article_chunks(embedding, article_id, top_k)

def retrieve_org_chunks(question: str, article_id: int, top_k: int = 5) -> list[ArticleChunk]:
    embedding = embed_query(question)
    return VectorDB.search_organization_chunks(embedding, article_id, top_k)

def retrieve_org_chunks_by_embedding(embedding: list[float], article_id: int, top_k: int = 20) -> list[ArticleChunk]:
    return VectorDB.search_organization_chunks(embedding, article_id, top_k, exclude_article_id=article_id)

def retrieve_article_chunks(article_id: int) -> list[ArticleChunk]:
    return VectorDB.get_article_chunks(article_id)

def build_context(chunks: list[ArticleChunk]) -> str:
    return "\n\n".join(chunk.content for chunk in chunks)