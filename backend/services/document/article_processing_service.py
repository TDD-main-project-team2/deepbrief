import logging
from hashlib import sha256
from pathlib import Path

from sqlalchemy.orm import Session

from backend.database.vector.vector_db import vector_db
from backend.models.article import Article
from backend.models.article_chunk import ArticleChunk
from backend.services.ai.embedding_service import embed_documents
from backend.services.ai.model_service import generate_article_metadata
from backend.services.document.document_service import DocumentResult, process_file
from backend.repositories import article_repository

logger = logging.getLogger(__name__)


def _article_metadata(document: DocumentResult) -> dict:
    """새 기사의 언론사·기자·카테고리·작성일을 모델로 채운다.

    Returns:
        dict: Article 컬럼 이름과 같은 키(media, author, category, published_at). 없는 값은 None.

    Notes:
        모델 실행이 실패해도 업로드는 막지 않는다. 실패하면 네 값 모두 None으로 두고 로그만 남긴다.
    """
    try:
        return generate_article_metadata(document)
    except Exception:
        logger.exception("기사 메타데이터 추출에 실패했습니다.")
        return {"media": None, "author": None, "category": None, "published_at": None}


def _embed_and_save_document_chunks(
    document: DocumentResult,
    article_id: int,
) -> None:
    """문서 청크를 임베딩하고 DB에 저장한다.

    Args:
        document (DocumentResult): 전처리와 청킹을 완료한 문서.
        article_id (int): DB에 저장 및 커밋된 기사의 기본키.

    Raises:
        ValueError: 청크가 없거나 청크 수와 벡터 수가 다른 경우.

    Notes:
        임베딩 생성 후 기존 청크를 새 청크로 교체한다.
        삭제와 저장은 하나의 트랜잭션으로 처리한다.
    """
    
    if not document.chunks:
        raise ValueError("저장할 문서 청크가 없습니다.")

    vectors = embed_documents(document.chunks)

    article_chunks = []
    for index, (content, vector) in enumerate(
        zip(document.chunks, vectors, strict=True)
    ):
        article_chunk = ArticleChunk(
            article_id=article_id,
            chunk_index=index,
            content=content,
            embedding=vector,
        )
        article_chunks.append(article_chunk)

    vector_db.replace_article_chunks(article_id, article_chunks)


def process_article(
    file_bytes: bytes,
    filename: str,
    db: Session,
    reprocess: bool = False,
) -> Article:
    """파일의 텍스트 추출부터 전처리, 청킹, 기사 등록, 임베딩, 벡터 DB 저장까지 전과정을 수행한다.

    전처리된 본문의 해시로 기존 기사를 찾고, 없으면 새 기사를 생성한다.
    기존 청크가 현재 청킹 결과와 같으면 재사용하며, 
    그렇지 않으면 청크를 임베딩하고 원문과 벡터를 함께 저장한다.

    Args:
        file_bytes (bytes): 처리할 파일의 바이너리 내용.
        filename (str): 파일 형식 판별에 사용할 확장자를 포함한 이름.
        db (Session): 기사 조회·생성에 사용할 DB 세션.
        reprocess (bool): True이면 기존 청크가 같아도 다시 임베딩하고 교체한다.
            기본값은 False이다.

    Returns:
        Article: 처리된 기사.(새로 저장한 기사 또는 동일한 본문 해시를 가진)

    Raises:
        ValueError: 본문·청크가 비어 있거나, 새 기사의 제목을 정할 수 없거나,
            청크 수와 생성된 벡터 수가 다른 경우.

    Notes:
        파일 → 텍스트 추출/OCR → 전처리 → 청킹 → 기사 조회/생성 → 임베딩 → 저장 순서다.
        모델 변경은 자동으로 감지하지 않으므로 reprocess=True를 전달해야 한다.
    """
    document = process_file(file_bytes, filename)
    if not document.text or not document.chunks:
        raise ValueError("저장할 기사 본문 또는 청크가 없습니다.")

    content_hash = sha256(document.text.encode("utf-8")).hexdigest()
    article = article_repository.get_by_content_hash(db, content_hash)

    if article is None:
        title = (document.title or Path(filename).stem).strip()
        if not title:
            raise ValueError("기사 제목 또는 파일 이름이 필요합니다.")
        article = Article(
            title=title[:255],
            body=document.text,
            content_hash=content_hash,
            **_article_metadata(document),
        )
        article_repository.create(db, article)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(article)

    if not reprocess:
        stored_chunks = vector_db.get_article_chunks(article.id)
        if stored_chunks and [chunk.content for chunk in stored_chunks] == document.chunks:
            return article

    _embed_and_save_document_chunks(document, article.id)

    return article