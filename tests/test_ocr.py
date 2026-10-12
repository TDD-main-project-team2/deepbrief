from types import SimpleNamespace
from unittest.mock import patch

from backend.services.document import ocr_service
from pathlib import Path
import pytest
import pymupdf

TEST_FILES = Path(__file__).parent / "test_files"
TEST_RESULTS = Path(__file__).parent / "test_results"

@pytest.mark.skip
def test_extract_pdf():
    path = TEST_FILES / "sample.pdf"
    result = ocr_service.extract_document(
        path.read_bytes(),
        path.name
    )
    output_path = get_next_result_path("result_pdf")
    output_path.write_text(result.text, encoding="utf-8")

    assert result.ocr_used is False

@pytest.mark.skip
def test_extract_scanned_pdf():
    path = TEST_FILES / "scan_pdf_news.pdf"
    result = ocr_service.extract_document(
        path.read_bytes(),
        path.name
    )
    output_path = get_next_result_path("result_scan_pdf")
    output_path.write_text(result.text, encoding="utf-8")
    assert result.ocr_used is True

@pytest.mark.skip
def test_extract_txt():
    path = TEST_FILES / "note.txt"
    result = ocr_service.extract_document(
        path.read_bytes(),
        path.name
    )
    output_path = get_next_result_path("result_txt")
    output_path.write_text(result.text, encoding="utf-8")

    assert result.ocr_used is False

@pytest.mark.skip
def test_extract_scan_png():
    path = TEST_FILES / "news_scan.png"
    result = ocr_service.extract_document(
        path.read_bytes(),
        path.name
    )
    output_path = get_next_result_path("result_scan_png")
    output_path.write_text(result.text, encoding="utf-8")

    assert result.ocr_used is True

def test_extract_pdf_with_images():
    path = TEST_FILES / "성남·과천·동탄은 흥행, 외곽은 미달…경기 청약 양극화.pdf"
    result = ocr_service.extract_document(
        path.read_bytes(),
        path.name
    )
    output_path = get_next_result_path("result_pdf_with_images")
    output_path.write_text(result.text, encoding="utf-8")

    assert result.ocr_used is True

def test_extract_unsupported():
    path = TEST_FILES / "OOO_경력소개서.docx"
    with pytest.raises(ocr_service.UnsupportedFormatError):
        ocr_service.extract_document(
            path.read_bytes(),
            path.name
        )

def test_ocr_engine_failure():
    with patch(
        "backend.services.document.ocr_service._paddleocr",
        side_effect=RuntimeError("OCR engine failed")
    ):
        with pytest.raises(ocr_service.OcrError):
            ocr_service._ocr(Path("fake.png"))

def test_extract_corrupt_pdf():
    path = TEST_FILES / "sample-corrupted.pdf"
    with pytest.raises(ocr_service.InvalidFileError):
        ocr_service.extract_document(
            path.read_bytes(),
            path.name
        )

def test_clean_ocr():
    input_text = "Hello world\n\n\nTest"
    expected = "Hello world Test"

    result = ocr_service._clean_ocr(input_text)

    assert result == expected

def test_markdown_table():
    rows = [
        ["Name", "Age"],
        ["John", "20"]
    ]
    expected = "| Name | Age |\n| --- | --- |\n| John | 20 |"

    result = ocr_service._markdown_table(rows)

    assert result == expected

def test_join():
    parts = ["Hello", "world"]

    result = ocr_service._join(parts)

    assert result == "Hello world"

def test_split():
    blocks = [
        ("doc_title", "Test Title"),
        ("body", "First paragraph"),
        ("body", "Second paragraph"),
        ("header", "Header text"),
    ]

    result = SimpleNamespace(
        title="",
        excluded_text=[]
    )

    body = ocr_service._split(blocks, result)

    assert result.title == "Test Title"
    assert result.excluded_text == ["Header text"]
    assert body == [
        {"text": "First paragraph", "full": False},
        {"text": "Second paragraph", "full": False},
    ]

def test_table():
    lines = [
        ("Name", (0, 0, 50, 20)),
        ("Age", (60, 0, 100, 20)),
        ("John", (0, 25, 50, 45)),
        ("20", (60, 25, 100, 45)),
    ]
    result = ocr_service._table(lines)
    assert result == "| Name | Age |\n| --- | --- |\n| John | 20 |"

def test_reading_order():
    boxes = [
        {
            "order": 2,
            "rect": pymupdf.Rect(0, 100, 100, 150),
        },
        {
            "order": 1,
            "rect": pymupdf.Rect(0, 0, 100, 50),
        },
    ]

    result = ocr_service._reading_order(boxes)

    assert result[0]["order"] == 1
    assert result[1]["order"] == 2

def get_next_result_path(name):
    i = 1

    while True:
        path = TEST_RESULTS / f"{name}_{i}.txt"

        if not path.exists():
            return path

        i += 1