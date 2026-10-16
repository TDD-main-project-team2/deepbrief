"""
OCR 결과를 전처리하고 임베딩용 청크로 구성한다.

ocr_service.py
    파일 → OCR/텍스트 추출 → OcrResult

document_service.py
    OcrResult → 전처리 → 청킹 → DocumentResult
"""

from dataclasses import dataclass, field

from .ocr_service import OcrResult, extract_document
from .preprocessing import preprocess_text
from .chunking import chunk_text


@dataclass
class DocumentResult:
    """AI 처리에 넘길 문서 구조."""

    title: str = ""
    text: str = ""
    chunks: list[str] = field(default_factory=list)
    meta_text: list[str] = field(default_factory=list)   # 언론사·기자 후보 줄 (OCR 뺀 글 중 일부, 메타데이터 추출용)


def process_document(result: OcrResult) -> DocumentResult:
    """
    OCR 결과를 전처리하고 청크로 분할한다.

    Args:
        result: OCR 서비스에서 반환한 결과

    Returns:
        제목, 전처리된 본문, 청크 목록을 담은 DocumentResult
    """
    title = result.title.strip()

    # 1. OCR 결과 텍스트 전처리
    cleaned_text = preprocess_text(result.text)

    # 2. 전처리된 텍스트를 청크로 분할
    chunks = chunk_text(cleaned_text)

    # 3. 문서 결과 구성
    return DocumentResult(
        title=title,
        text=cleaned_text,
        chunks=chunks,
        meta_text=list(result.meta_text),
    )


def process_file(file_bytes: bytes, filename: str) -> DocumentResult:
    """
    파일 입력부터 OCR, 전처리, 청킹까지 한 번에 수행한다.
    """
    result = extract_document(file_bytes, filename)
    return process_document(result)
