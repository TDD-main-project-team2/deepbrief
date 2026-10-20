import os
from functools import lru_cache

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

MODEL_NAME = os.environ["EMBEDDING_MODEL"]

@lru_cache(maxsize=1)
def _get_embedding_model() -> SentenceTransformer:
    """임베딩 모델을 로드하고 캐시된 인스턴스를 반환한다.

    Args:
        None

    Returns:
        SentenceTransformer: 문서와 질문의 벡터화에 사용할 임베딩 모델.

    Notes:
        최초 호출 시 모델을 로드하며 이후 호출에서는 같은 인스턴스를 재사용한다.
        로컬 캐시에 모델이 없으면 Hugging Face에서 다운로드한다.
    """
    return SentenceTransformer(MODEL_NAME)


def embed_documents(texts: list[str]) -> list[list[float]]:
    """문서 청크 목록을 정규화된 임베딩 벡터 목록으로 변환한다.

    Args:
        texts (list[str]): 벡터화할 문서의 청크 문자열 목록.

    Returns:
        list[list[float]]: 입력 순서에 대응하는 1,024차원 벡터 목록.
        입력 목록이 비어 있으면 빈 목록을 반환한다.
    """
    if not texts:
        return []

    vectors = _get_embedding_model().encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    return vectors


def embed_query(text: str) -> list[float]:
    """검색 질문을 정규화된 임베딩 벡터로 변환한다.

    Args:
        text (str): 관련 문서 청크를 검색할 질문 문자열.

    Returns:
        list[float]: 질문에 대응하는 1,024차원 벡터.

    Notes:
        BGE-m3 모델은 질문용 접두어 없이 원문 질문을 임베딩한다.
        snowflake 모델로 변경 시 'prompt_name='로 질문용 접두어를 붙여야 한다.
        (예: prompt_name="query" -> "query: {text}")
    """
    vector = _get_embedding_model().encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    return vector
