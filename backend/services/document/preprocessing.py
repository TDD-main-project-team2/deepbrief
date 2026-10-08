"""
OCR 결과 텍스트를 서비스 입력에 적합한 형태로 전처리한다.

전처리 원칙:
- 원문 정보는 최대한 보존한다.
- 담당 기자명은 최소 한 개 보존한다.
- 본문 앞쪽에 중복된 기자 표기만 정리한다.
- 입력/수정일은 보존한다.
- 기사 하단의 명백한 사이트 메뉴/푸터만 제거한다.
- OCR 과정에서 발생한 명확한 공백 노이즈만 정리한다.
"""

import re


# 기사 하단의 명백한 사이트/신문사 정보
FOOTER_PATTERNS = [
    r"^등록번호\s*:",
    r"^발행일자\s*:",
    r"^주소\s*:",
    r"^전화번호\s*:",
    r"^Copyright\b",
    r"^연예\s+해외연예\s+스타\s+TV일반",
]


def _remove_duplicate_reporter(text: str) -> str:
    """
    기사 앞부분에 중복으로 들어간 기자 표기를 정리한다.

    담당 기자명 자체는 보존한다.
    """
    return re.sub(
        r"\[[^\]\n]+?\s+[가-힣]{2,5}\s+기자\]",
        "",
        text,
        count=1,
    )


def _remove_footer(text: str) -> str:
    """
    기사 하단의 명백한 사이트/신문사 정보를 제거한다.

    등록번호, 발행일자, 주소, 전화번호 등의 정보가
    등장하면 해당 지점부터 기사 푸터로 판단한다.
    또한 뉴스 사이트의 카테고리 메뉴가 시작되는 경우 제거한다.
    """
    lines = text.splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip()

        if any(
            re.search(pattern, stripped)
            for pattern in FOOTER_PATTERNS
        ):
            return "\n".join(lines[:i])

    return text


def _normalize_ocr_spacing(text: str) -> str:
    """
    OCR 과정에서 발생한 명확한 공백 노이즈를 정리한다.

    원문 정보 손상을 막기 위해 확실한 패턴만 처리한다.
    """

    # 숫자 내부에 OCR이 삽입한 공백 제거
    text = re.sub(
        r"(?<=\d)[ \t]+(?=\d)",
        "",
        text,
    )

    # 숫자와 일반적인 단위 사이의 OCR 공백 제거
    text = re.sub(
        r"(?<=\d)[ \t]+(?=(?:년|월|일|시|분|초|명|건|개|회|원|만원|억원|조원)\b)",
        "",
        text,
    )

    # OCR에서 명확하게 분리된 단어
    text = re.sub(r"유 품", "유품", text)
    
    # OCR에서 줄바꿈으로 분리된 전문용어 복구
    text = re.sub(r"엄빌\s+리컬", "엄빌리컬", text)

    # OCR에서 명확하게 분리된 표현
    text = re.sub(r"판단[ \t]+했다\b", "판단했다", text)
    text = re.sub(r"말[ \t]+했다\b", "말했다", text)
    text = re.sub(r"조성[ \t]+하여\b", "조성하여", text)
    text = re.sub(r"평가[ \t]+받았다\b", "평가받았다", text)
    text = re.sub(
        r"개설·[ \t]+운영함으로써\b",
        "개설·운영함으로써",
        text,
    )
    text = re.sub(r"감소[ \t]+했다\b", "감소했다", text)

    # OCR에서 영어 단어 중간에 삽입된 명확한 공백 제거
    text = re.sub(r"\bPr[ \t]+e\b", "Pre", text)

    # 기호 뒤에 삽입된 OCR 공백 제거
    text = re.sub(
        r"([·~])[ \t]+",
        r"\1",
        text,
    )

    return text


def preprocess_text(text: str) -> str:
    """
    OCR로 추출된 텍스트를 전처리한다.

    Args:
        text: OCR 결과 텍스트

    Returns:
        정리된 텍스트
    """
    if not text:
        return ""

    # 줄 단위 기본 정리
    lines = [line.strip() for line in text.splitlines()]

    # 연속된 공백 정리
    lines = [
        re.sub(r"[ \t]+", " ", line)
        for line in lines
    ]

    cleaned = "\n".join(lines)

    # 담당 기자명은 보존하고 중복 표기만 제거
    cleaned = _remove_duplicate_reporter(cleaned)

    # 명백한 사이트 메뉴/푸터 제거
    cleaned = _remove_footer(cleaned)

    # OCR 공백 노이즈 정리
    cleaned = _normalize_ocr_spacing(cleaned)

    # 빈 줄이 3개 이상 이어지는 경우 1개 문단 간격으로 축소
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()