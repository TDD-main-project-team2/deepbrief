"""
뉴스 기사 파일에서 텍스트를 추출한다.

    result = extract_document(file_bytes, filename)

pdf            글자 정보가 있는 쪽은 레이아웃 모델로 영역·순서만 잡고 PyMuPDF로 글자를 꺼낸다.
               글자 정보가 없는 쪽(스캔본)은 PaddleOCR-VL로 읽는다.
png, jpg, jpeg PaddleOCR-VL로 읽는다.
txt, md        그대로 읽는다.
"""
from __future__ import annotations

import html
import re
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pymupdf

IMAGE_EXT = {".png", ".jpg", ".jpeg"}
TEXT_EXT = {".txt", ".md"}
SCALE = 2.0                                  # 쪽을 이미지로 만들 때의 배율 (144dpi)
EXCLUDED = {"header", "header_image", "footer", "footer_image", "number"}
IMAGE = {"image", "figure", "chart", "seal"}
SENTENCE_END = ".!?…\"”’)"
GROUP_GAP = 15                               # 순서 없는 영역(표 제목·표·각주)을 한 묶음으로 보는 세로 간격 (pt)
CAPTION_GAP = 20                             # 사진 바로 밑 설명글로 보는 세로 간격 (pt)
IMAGE_TEXT = {"table", "text", "paragraph_title", "figure_title", "vision_footnote"}     # 이미지 속에서 글로 읽을 영역
IMAGE_PAD = 3                                # 이미지 속 글을 잘라낼 때 이웃 영역과 띄우는 간격 (pt)


class OcrServiceError(Exception):
    """이 모듈이 내는 오류의 공통 부모."""


class UnsupportedFormatError(OcrServiceError):
    """지원하지 않는 확장자."""


class InvalidFileError(OcrServiceError):
    """깨진 파일, 암호가 걸린 PDF, 읽을 수 없는 텍스트."""


class OcrError(OcrServiceError):
    """레이아웃·OCR 모델 실행 실패."""


@dataclass
class OcrResult:
    text: str = ""                                            # 본문 (문단은 빈 줄로 구분)
    title: str = ""                                           # 기사 제목 (못 찾으면 빈 값)
    page_count: int = 1
    ocr_used: bool = False                                    # OCR로 읽은 부분이 있는지
    excluded_text: list[str] = field(default_factory=list)    # 본문에서 뺀 글 (머리말, 꼬리말, 메뉴 등)


_models: dict = {}
_lock = threading.Lock()


def _paddleocr():
    """paddleocr 모듈을 불러온다. Windows에서는 torch를 Paddle보다 나중에 불러오면 torch의 DLL 로드가 실패하므로,
    torch가 설치돼 있으면 먼저 불러온다."""
    try:
        import torch  # noqa: F401
    except ImportError:
        pass
    import paddleocr
    return paddleocr


def _layout(page):
    """쪽의 영역 목록 [{label, order, rect, lines}]. 글자는 읽지 않고 영역과 순서만 잡는다."""
    pix = page.get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE), alpha=False)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    try:
        with _lock:
            if "layout" not in _models:
                _models["layout"] = _paddleocr().LayoutDetection(model_name="PP-DocLayoutV3")
            res = _models["layout"].predict(np.ascontiguousarray(rgb[:, :, ::-1]), batch_size=1, layout_nms=True)[0]
    except Exception as error:
        raise OcrError(f"레이아웃 모델 실행에 실패했습니다: {error}") from error
    return [{"label": b["label"], "order": b.get("order"), "lines": [],
             "rect": pymupdf.Rect([c / SCALE for c in b["coordinate"]])} for b in res["boxes"]]


def _ocr(image_path):
    """이미지 파일을 PaddleOCR-VL로 읽는다. [(종류, 글)] 목록."""
    try:
        with _lock:
            if "ocr" not in _models:
                _models["ocr"] = _paddleocr().PaddleOCRVL(pipeline_version="v1.6")
            results = _models["ocr"].predict(str(image_path))
        blocks = [(b["block_label"], (b["block_content"] or "").strip())
                  for res in results for b in res.json["res"]["parsing_res_list"]]
    except Exception as error:
        raise OcrError(f"OCR 실행에 실패했습니다: {error}") from error
    return [(label, _clean_ocr(text)) for label, text in blocks if text]


def _clean_ocr(text):
    """OCR 결과 정리: 수식 표기 조각을 지우고, 표는 글로 풀고, 끊긴 줄은 잇는다."""
    text = re.sub(r"\s*\$ [^$\n]{0,30} \$\s*", "", text)                     # 아이콘 등을 수식으로 잘못 읽은 조각
    if "<table" in text:
        rows = [[html.unescape(cell).replace("\\n", " ").strip() for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
                for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S)]
        return _markdown_table(rows, single_column="\n\n")
    return _join([line for line in text.split("\n") if line.strip()])


def _join(texts):
    """줄바꿈으로 끊긴 글을 한 문단으로 잇는다. 줄 사이를 띄울지는 한국어 분석기(Kiwi)가 판단한다."""
    texts = [text.strip() for text in texts]
    if len(texts) < 2:
        return "".join(texts)
    with _lock:
        if "kiwi" not in _models:
            from kiwipiepy import Kiwi
            _models["kiwi"] = Kiwi()
        spaces = _models["kiwi"].glue(texts, return_space_insertions=True)[1]
    out = texts[0]
    for prev, nxt, space in zip(texts, texts[1:], spaces):
        out += (" " if space and not prev.endswith("=") else "") + nxt
    return out


def _read_lines(page):
    """쪽의 줄 목록 [(글, bbox)]."""
    return [(text, line["bbox"])
            for block in page.get_text("dict", sort=True)["blocks"] for line in block.get("lines", [])
            if (text := "".join(span["text"] for span in line["spans"]).replace("\xa0", " ")).strip()]


def _paragraph(lines):
    """한 영역의 줄들을 문단으로 만든다. (글, 꽉 찬 줄로 끝났는지)를 돌려준다."""
    right = max(bbox[2] for _, bbox in lines)
    groups = [[lines[0][0]]]
    for (text, bbox), (nxt, nb) in zip(lines, lines[1:]):
        height = nb[3] - nb[1]
        first_word = sum(height * (1.0 if ch > "⺀" else 0.55) for ch in nxt.split()[0])
        same_row = abs(nb[1] - bbox[1]) < height / 2
        if not same_row and bbox[2] + first_word > right:     # 다음 단어가 들어갈 자리가 없었음 → 자동 줄바꿈
            groups[-1].append(nxt)
        else:                                                 # 실제 줄바꿈
            groups.append([nxt])
    last = lines[-1][1]
    full = len(groups[-1]) > 1 and right - last[2] < 2 * (last[3] - last[1])
    return "\n".join(_join(group) for group in groups), full


def _markdown_table(rows, single_column="\n"):
    """행 목록 [[칸, ...]]을 마크다운 표로 만든다. 첫 행이 머리글이다. 열이 하나뿐이면 표로 만들지 않고 줄로 잇는다."""
    rows = [row for row in rows if any(row)]
    width = max((len(row) for row in rows), default=0)
    if width < 2:
        return single_column.join(row[0] for row in rows)
    lines = ["| " + " | ".join(cell.replace("\n", " ").replace("|", "\\|") for cell in row + [""] * (width - len(row))) + " |"
             for row in rows]
    lines.insert(1, "| " + " | ".join(["---"] * width) + " |")
    return "\n".join(lines)


def _table(lines):
    """표 영역의 글을 마크다운 표로 만든다. 세로로 겹치는 글은 같은 행, 가로로 겹치는 글은 같은 열로 본다."""
    rows = []
    for text, bbox in sorted(lines, key=lambda line: (line[1][1], line[1][0])):
        if rows and bbox[1] < rows[-1]["bottom"] - (bbox[3] - bbox[1]) * 0.3:
            rows[-1]["cells"].append((bbox[0], bbox[2], text.strip()))
            rows[-1]["bottom"] = max(rows[-1]["bottom"], bbox[3])
        else:
            rows.append({"bottom": bbox[3], "cells": [(bbox[0], bbox[2], text.strip())]})
    columns = []                                              # 열의 가로 범위 [왼쪽, 오른쪽]
    for x0, x1, _ in sorted(cell for row in rows for cell in row["cells"]):
        if columns and x0 < columns[-1][1]:
            columns[-1][1] = max(columns[-1][1], x1)
        else:
            columns.append([x0, x1])
    table = []
    for row in rows:
        cells = [""] * len(columns)
        for x0, _, text in sorted(row["cells"]):
            index = next(i for i, column in enumerate(columns) if x0 < column[1])
            cells[index] = f"{cells[index]} {text}".strip()
        table.append(cells)
    return _markdown_table(table)


def _x_overlap(a, b):
    return min(a.x1, b.x1) > max(a.x0, b.x0)


def _reading_order(boxes):
    """order가 있는 영역은 그 순서대로 둔다. order가 없는 영역(표·그림·표 제목·각주)은 위아래로 붙은 것끼리 묶어서,
    그 묶음 위에 있으면서 가로로 겹치는 마지막 영역 뒤에 둔다."""
    ordered = sorted((b for b in boxes if b["order"] is not None), key=lambda b: b["order"])
    groups = []
    for box in sorted((b for b in boxes if b["order"] is None), key=lambda b: b["rect"].y0):
        rect = box["rect"]
        group = next((g for g in reversed(groups)
                      if rect.y0 - g["rect"].y1 < GROUP_GAP and _x_overlap(rect, g["rect"])), None)
        if group:
            group["boxes"].append(box)
            group["rect"] |= rect
        else:
            groups.append({"rect": pymupdf.Rect(rect), "boxes": [box]})
    for group in groups:
        above = [i for i, o in enumerate(ordered)
                 if o["rect"].y0 <= group["rect"].y0 and _x_overlap(o["rect"], group["rect"])]
        at = max(above) + 1 if above else 0
        ordered[at:at] = group["boxes"]
    return ordered


def _continued(line, boxes):
    """어느 영역에도 들지 못한 줄이 바로 위 문단에서 이어지는 줄이면 그 영역을 돌려준다.
    (쪽 맨 아래 본문 줄이 꼬리말로 잘못 잡히는 경우를 되살린다.)"""
    x0, y0, x1, y1 = line[1]
    height = y1 - y0
    for box in boxes:
        if len(box["lines"]) < 2 or box["label"] in EXCLUDED | IMAGE | {"table"}:     # 한 줄짜리 영역은 꽉 찬 줄인지 알 수 없다
            continue
        last = max(box["lines"], key=lambda item: item[1][3])[1]
        left = min(bbox[0] for _, bbox in box["lines"])
        right = max(bbox[2] for _, bbox in box["lines"])
        if (abs(x0 - left) < height / 2 and -1 < y0 - last[3] < height            # 왼쪽 끝이 같고 바로 아랫줄
                and abs(height - (last[3] - last[1])) < height * 0.2               # 글자 크기가 같음
                and right - last[2] < 2 * height):                                 # 윗줄이 꽉 찬 줄
            return box
    return None


def _read_image_text(page, boxes, result, tmp):
    """글자 정보 없이 이미지로만 들어 있는 표와 글을 OCR로 읽는다. 읽은 영역들은 그 자리의 영역 하나로 바꾼다.
    이미지 안에 표가 있거나 글 영역이 둘 이상일 때만 읽는다. (하나뿐인 글 영역은 아이콘·배너인 경우가 많다.)"""
    images = sorted((pymupdf.Rect(info["bbox"]) for info in page.get_image_info()), key=lambda rect: rect.get_area())
    for number, image in enumerate(images):
        inside = [b for b in boxes if not b["lines"] and b["label"] in IMAGE_TEXT
                  and (b["rect"] & image).get_area() > b["rect"].get_area() * 0.8]
        labels = [b["label"] for b in inside]
        if "table" not in labels and labels.count("text") + labels.count("paragraph_title") < 2:
            continue
        area = pymupdf.Rect(inside[0]["rect"])
        for box in inside:
            area |= box["rect"]
        others = [b["rect"] for b in boxes if not any(b is box for box in inside) and _x_overlap(b["rect"], area)]
        top = max([image.y0] + [r.y1 for r in others if r.y1 <= area.y0 + IMAGE_PAD])       # 영역으로 잡히지 않은 제목·머리글까지
        bottom = min([image.y1] + [r.y0 for r in others if r.y0 >= area.y1 - IMAGE_PAD])    # 넓히되, 사진 같은 이웃 영역은 넘지 않는다
        clip = pymupdf.Rect(min(image.x0, area.x0), min(top + IMAGE_PAD, area.y0),
                            max(image.x1, area.x1), max(bottom - IMAGE_PAD, area.y1)) & page.rect
        path = Path(tmp) / f"region{number}.png"
        page.get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE), clip=clip, alpha=False).save(path)
        result.ocr_used = True
        orders = [b["order"] for b in inside if b["order"] is not None]
        boxes[:] = [b for b in boxes if not any(b is box for box in inside)]
        boxes.append({"label": "image_text", "order": min(orders, default=None), "rect": area, "lines": [],
                      "blocks": _ocr(path)})


def _extract_page(page, result, tmp):
    """한 쪽의 본문 문단 목록 [{text, full}]을 돌려준다. 제목과 뺀 글은 result에 넣는다."""
    lines = _read_lines(page)
    if not lines:
        if not page.get_images():
            return []                                         # 빈 쪽
        result.ocr_used = True                                # 글자 정보가 없는 쪽(스캔본)
        path = Path(tmp) / "page.png"
        page.get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE), alpha=False).save(path)
        return _split(_ocr(path), result)

    boxes = _layout(page)
    loose = []                                                # 어느 영역에도 제대로 들지 못한 줄
    for line in lines:                                        # 각 줄을 가장 많이 겹치는 영역에 넣는다
        x0, y0, x1, y1 = line[1]
        overlap = [min(x1, b["rect"].x1) - max(x0, b["rect"].x0)
                   if b["rect"].y0 - 1 <= (y0 + y1) / 2 <= b["rect"].y1 + 1 else 0 for b in boxes]
        best = max(range(len(boxes)), key=overlap.__getitem__, default=None)
        if best is None or overlap[best] <= 0:
            loose.append(line)
        elif boxes[best]["label"] in EXCLUDED and overlap[best] < (x1 - x0) / 2:    # 뺄 영역에 절반도 안 걸친 줄
            loose.append(line)
        else:
            boxes[best]["lines"].append(line)
    for line in sorted(loose, key=lambda item: item[1][1]):
        owner = _continued(line, boxes)
        if owner:
            owner["lines"].append(line)
        else:
            result.excluded_text.append(line[0].strip())
    _read_image_text(page, boxes, result, tmp)
    images = [b["rect"] for b in boxes if b["label"] in IMAGE]

    body = []
    for box in _reading_order(boxes):
        label, own = box["label"], box["lines"]
        if label == "image_text":                             # 이미지에서 OCR로 읽은 표와 글
            body += [{"text": text, "full": False} for _, text in box["blocks"]]
            continue
        if not own:
            continue
        caption = label == "vision_footnote" and any(                         # 사진 바로 밑 설명글
            -5 < box["rect"].y0 - image.y1 < CAPTION_GAP and _x_overlap(box["rect"], image) for image in images)
        if label in EXCLUDED or label in IMAGE or caption:
            result.excluded_text += [text.strip() for text, _ in own]
        elif label == "table":
            body.append({"text": _table(own), "full": False})
        elif label == "doc_title" and not result.title:
            result.title = _paragraph(own)[0].replace("\n", " ")
        else:
            text, full = _paragraph(own)
            body.append({"text": text, "full": full})
    return body


def _split(blocks, result):
    """OCR 블록을 제목, 본문, 뺀 글로 나눈다."""
    body = []
    for label, text in blocks:
        if label in EXCLUDED:
            result.excluded_text.append(text)
        elif label == "doc_title" and not result.title:
            result.title = text
        else:
            body.append({"text": text, "full": False})
    return body


def _extract_pdf(file_bytes, result, tmp):
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as error:
        raise InvalidFileError(f"PDF를 열 수 없습니다: {error}") from error
    with doc:
        if doc.needs_pass:
            raise InvalidFileError("암호가 걸린 PDF는 읽을 수 없습니다.")
        result.page_count = doc.page_count
        merged = []
        for page in doc:
            body = _extract_page(page, result, tmp)
            prev = merged[-1] if merged else None
            if prev and body and prev["full"] and prev["text"][-1] not in SENTENCE_END:    # 쪽을 넘어가는 문단
                first = body.pop(0)
                prev["text"] = _join([prev["text"], first["text"]])
                prev["full"] = first["full"]
            merged += body
    return merged


def extract_document(file_bytes: bytes, filename: str) -> OcrResult:
    """파일에서 텍스트를 추출한다. 형식은 파일 이름의 확장자로 판별한다."""
    ext = Path(filename or "").suffix.lower()
    result = OcrResult()
    if ext in TEXT_EXT:
        try:
            result.text = file_bytes.decode("utf-8-sig").replace("\r\n", "\n").strip()
        except UnicodeDecodeError as error:
            raise InvalidFileError("텍스트 파일은 UTF-8 인코딩이어야 합니다.") from error
        return result
    if ext not in IMAGE_EXT | {".pdf"}:
        raise UnsupportedFormatError(f"지원하지 않는 형식입니다: {ext or '(확장자 없음)'}")

    with tempfile.TemporaryDirectory() as tmp:
        if ext == ".pdf":
            body = _extract_pdf(file_bytes, result, tmp)
        else:
            result.ocr_used = True
            path = Path(tmp) / f"image{ext}"
            path.write_bytes(file_bytes)
            body = _split(_ocr(path), result)
    result.text = "\n\n".join(part["text"] for part in body)
    return result
