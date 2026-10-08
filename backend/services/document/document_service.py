"""
OCR 결과를 AI 처리용 문서 구조로 정리한다.

ocr_service.py
    파일 → OCR/텍스트 추출 → OcrResult

document_service.py
    OcrResult → DocumentResult
"""

from dataclasses import dataclass

from .ocr_service import OcrResult


@dataclass
class DocumentResult:
    """AI 처리에 넘길 문서 구조."""
    title: str = ""
    text: str = ""


def process_document(result: OcrResult) -> DocumentResult:
    """
    OcrResult를 AI 처리용 문서 구조로 변환한다.
    """
    return DocumentResult(
        title=result.title.strip(),
        text=result.text.strip(),
    )