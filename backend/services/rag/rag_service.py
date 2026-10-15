from backend.database.vector import vector_db
from backend.services.ai.embedding_service import embed_query
from backend.models.article_chunk import ArticleChunk

def retrieve_article_chunks(question: str, article_id: int, top_k: int = 5) -> list[ArticleChunk]:
    embedding = embed_query(question)
    return vector_db.search_similar_chunks(embedding, top_k, article_id)

def retrieve_all_chunks(question: str, top_k: int = 5) -> list[ArticleChunk]:
    embedding = embed_query(question)
    return vector_db.search_similar_chunks(embedding, top_k)

def build_context(chunks: list[ArticleChunk]) -> str:
    return "\n\n".join(chunk.content for chunk in chunks)