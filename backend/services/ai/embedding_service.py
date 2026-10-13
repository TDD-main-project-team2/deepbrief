from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "dragonkue/snowflake-arctic-embed-l-v2.0-ko"

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
