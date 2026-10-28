"""
전처리된 텍스트를 임베딩 단위의 청크로 나눈다.

청킹 원칙:
- 문단 구조를 최대한 유지한다.
- 긴 문단은 한국어 문장 단위로 나눈다.
- 하나의 문장이 너무 길 경우에만 강제로 분할한다.
- 원문 내용은 변경하지 않는다.
- 필요할 경우 인접 청크 간 문장 단위 overlap을 적용한다.
- 일반 텍스트는 max_length를 기준으로 분할한다.
- 표는 max_length를 초과하더라도 하나의 청크로 유지한다.
- 표 내부의 행이나 셀은 분할하지 않는다.
"""

from kiwipiepy import Kiwi


# 기본 최대 청크 길이
MAX_CHUNK_LENGTH = 300

kiwi = Kiwi()


def _is_table(paragraph: str) -> bool:
    """
    하나의 문단이 Markdown 표인지 확인한다.

    Markdown 표는 최소한
        | 헤더 | 헤더 |
        | --- | --- |
    형태를 가진다고 본다.

    표 내부의 내용은 수정하지 않는다.
    """
    lines = [
        line.strip()
        for line in paragraph.splitlines()
        if line.strip()
    ]

    if len(lines) < 2:
        return False

    # 첫 줄과 두 번째 줄이 모두 | 로 구성된 Markdown 표 형태인지 확인
    if not (lines[0].startswith("|") and lines[0].endswith("|")):
        return False

    separator = lines[1]

    if not (separator.startswith("|") and separator.endswith("|")):
        return False

    cells = [
        cell.strip()
        for cell in separator.strip("|").split("|")
    ]

    if not cells:
        return False

    return all(
        cell
        and all(char in "-: " for char in cell)
        and "-" in cell
        for cell in cells
    )


def split_long_paragraph(
    paragraph: str,
    max_length: int,
) -> list[str]:
    """
    긴 문단을 한국어 문장 단위로 나눈다.

    하나의 문장 자체가 max_length를 넘으면
    마지막 수단으로 문자 단위 강제 분할한다.
    """
    if len(paragraph) <= max_length:
        return [paragraph]

    sentences = kiwi.split_into_sents(paragraph)

    chunks = []
    current = ""

    for sentence in sentences:
        text = sentence.text.strip()

        if not text:
            continue

        # 문장 자체가 최대 길이를 초과하는 경우
        if len(text) > max_length:
            if current:
                chunks.append(current.strip())
                current = ""

            for i in range(0, len(text), max_length):
                chunks.append(text[i:i + max_length])

            continue

        # 첫 문장
        if not current:
            current = text

        # 현재 청크에 문장을 추가할 수 있는 경우
        elif len(current) + 1 + len(text) <= max_length:
            current += " " + text

        # 추가할 수 없는 경우 새로운 청크 시작
        else:
            chunks.append(current.strip())
            current = text

    if current:
        chunks.append(current.strip())

    return chunks


def _get_sentences(text: str) -> list[str]:
    """
    텍스트를 문장 단위로 분리한다.
    """
    return [
        sentence.text.strip()
        for sentence in kiwi.split_into_sents(text)
        if sentence.text.strip()
    ]


def apply_sentence_overlap(
    chunks: list[str],
    overlap: int,
    max_length: int,
) -> list[str]:
    """
    인접 청크 간 문장 단위 overlap을 적용한다.

    표 청크에는 overlap을 적용하지 않는다.

    overlap:
        다음 청크에 포함할 이전 청크의 마지막 문장 수

    overlap을 추가한 결과가 max_length를 초과하면
    가능한 범위까지만 overlap을 적용한다.
    """
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    overlapped_chunks = [chunks[0]]

    for index in range(1, len(chunks)):
        previous = chunks[index - 1]
        current = chunks[index]

        # 표는 하나의 청크로 보호한다.
        # 표 자체를 다음 청크에 복제하지 않는다.
        if _is_table(previous) or _is_table(current):
            overlapped_chunks.append(current)
            continue

        previous_sentences = _get_sentences(previous)

        if not previous_sentences:
            overlapped_chunks.append(current)
            continue

        overlap_sentences = previous_sentences[-overlap:]

        selected_overlap = []

        # overlap 문장을 뒤에서부터 하나씩 추가한다.
        # 현재 청크와 합쳐도 max_length를 넘지 않는 경우에만 사용한다.
        for sentence in reversed(overlap_sentences):
            candidate_sentences = [sentence] + selected_overlap
            prefix = "\n\n".join(candidate_sentences)

            candidate = prefix + "\n\n" + current

            if len(candidate) <= max_length:
                selected_overlap = candidate_sentences
            else:
                break

        if selected_overlap:
            prefix = "\n\n".join(selected_overlap)

            overlapped_chunks.append(
                prefix + "\n\n" + current
            )
        else:
            overlapped_chunks.append(current)

    return overlapped_chunks


def chunk_text(
    text: str,
    max_length: int = MAX_CHUNK_LENGTH,
    overlap: int = 0,
) -> list[str]:
    """
    전처리된 텍스트를 청크로 분할한다.

    일반 텍스트:
        max_length를 기준으로 분할한다.

    표:
        max_length를 초과하더라도 하나의 청크로 유지한다.
        표 내부 행/셀은 분할하지 않는다.

    Args:
        text:
            전처리된 텍스트

        max_length:
            일반 텍스트의 최대 청크 문자 수

        overlap:
            인접 일반 텍스트 청크 간 겹칠 문장 수.
            0이면 overlap 없이 분할한다.

    Returns:
        청크 문자열 리스트
    """
    if not text:
        return []

    if max_length <= 0:
        raise ValueError(
            "max_length는 1 이상이어야 합니다."
        )

    if overlap < 0:
        raise ValueError(
            "overlap은 0 이상이어야 합니다."
        )

    if overlap >= max_length:
        raise ValueError(
            "overlap은 max_length보다 작아야 합니다."
        )

    # 빈 줄을 기준으로 문단 분리
    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:

        # ---------------------------------------------------------
        # 표 보호
        # ---------------------------------------------------------
        # 표는 크기와 관계없이 하나의 청크로 유지한다.
        if _is_table(paragraph):

            # 현재 일반 텍스트가 있으면 먼저 저장
            if current:
                chunks.append(current.strip())
                current = ""

            # 표는 max_length를 초과해도 그대로 저장
            chunks.append(paragraph)

            continue

        # ---------------------------------------------------------
        # 일반 텍스트
        # ---------------------------------------------------------

        # 짧은 문단
        if len(paragraph) <= max_length:

            if not current:
                current = paragraph

            elif len(current) + 2 + len(paragraph) <= max_length:
                current += "\n\n" + paragraph

            else:
                chunks.append(current.strip())
                current = paragraph

        # 긴 문단
        else:

            if current:
                chunks.append(current.strip())
                current = ""

            chunks.extend(
                split_long_paragraph(
                    paragraph,
                    max_length,
                )
            )

    if current:
        chunks.append(current.strip())

    # overlap이 없으면 기본 청킹 결과 그대로 반환
    if overlap == 0:
        return chunks

    return apply_sentence_overlap(
        chunks,
        overlap,
        max_length,
    )