"""
QA 파인튜닝 데이터셋 가공 (정제 + 구성)

원본(AI Hub 뉴스 기사 기계독해 데이터)을 읽어 정제한 뒤
Training / Validation / Golden 데이터셋을 만들어 저장한다.
설정은 같은 폴더의 config.yaml 에서 읽는다.

실행 (레포 루트에서)
    python backend/fine_tuning/qa/data_preparation.py

처리 순서
    1. 유형별 원본 로드 (메모리 절약을 위해 파일 1개씩)
    2. 정제
       - 빈 질문/본문/답 제외
       - answer_start 위치 오류 제외
       - 본문·답 정규화 후 답 위치 재확인, 맞지 않으면 제외
       - 같은 본문은 1건만 남김 (완전 중복 포함)
    3. 기사당 질문 1개 선택
       - 같은 원본 안에서 다른 유형 파일과 겹치는 기사 제외
    4. Training 후보에서 Validation 원본(VL)과 겹치는 기사 제외
    5. 샘플링 (유형별 수량, 예/아니오 비율, Golden은 분야별 균등)
    6. Training 순서 배치 (chunk_size 구간마다 유형·예/아니오 비율 동일)
    7. 저장 + 단계별 건수 출력
"""

import json
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
RAW_DIR_ENV = "FT_RAW_DIR"

# 원본 구분: AI Hub가 나눠둔 Training(TL_) / Validation(VL_)
SOURCE_SPLITS = {
    "training": {"folder": "Training", "prefix": "TL"},
    "validation": {"folder": "Validation", "prefix": "VL"},
}

# 각 데이터셋을 뽑아올 원본 (validation과 golden은 같은 VL에서 서로 겹치지 않게)
SPLIT_SOURCES = {"training": "training", "validation": "validation", "golden": "validation"}

# 원본 유형 (파일명 기준) 과 한글 이름
QA_TYPES = ("span_extraction", "span_inference", "text_entailment", "unanswerable")

# 정제 순서. 같은 기사가 여러 유형 파일에 있으면 먼저 처리한 유형에 남긴다.
# 원본 수량이 적은 유형부터 처리해, 부족한 유형의 후보가 줄지 않게 한다.
CLEANING_ORDER = ("unanswerable", "text_entailment", "span_inference", "span_extraction")
QA_TYPE_LABELS = {
    "span_extraction": "추출형",
    "span_inference": "추론형",
    "text_entailment": "Yes/No 단문형",
    "unanswerable": "응답불가형",
}

# 결과 파일명
OUTPUT_FILENAMES = {
    "training": "training_dataset.json",
    "validation": "validation_dataset.json",
    "golden": "golden_dataset.json",
}


def load_config() -> dict:
    """config.yaml 을 읽는다."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_raw_dir(config: dict) -> Path:
    """원본 폴더. config의 raw_dir이 없으면 환경변수 FT_RAW_DIR 를 쓴다."""
    value = config["paths"].get("raw_dir") or os.environ.get(RAW_DIR_ENV)
    if not value:
        raise RuntimeError(
            f"원본 폴더 경로가 없습니다. 환경변수 {RAW_DIR_ENV} 를 설정하거나 "
            f"config.yaml 의 paths.raw_dir 에 경로를 적으세요."
        )
    raw_dir = Path(value)
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"원본 폴더가 없습니다: {raw_dir}")
    return raw_dir


def get_processed_dir(config: dict) -> Path:
    """가공 결과 폴더. config의 processed_dir이 없으면 qa/data/processed 를 쓰고, 없으면 만든다."""
    value = config["paths"].get("processed_dir")
    processed_dir = Path(value) if value else BASE_DIR / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    return processed_dir


def get_raw_file(config: dict, source_split: str, qa_type: str) -> Path:
    """원본 json 경로. 예: (training, unanswerable) -> .../Training/TL_unanswerable.json"""
    source = SOURCE_SPLITS[source_split]
    return get_raw_dir(config) / source["folder"] / f"{source['prefix']}_{qa_type}.json"


def get_output_file(config: dict, split: str) -> Path:
    return get_processed_dir(config) / OUTPUT_FILENAMES[split]


def get_type_counts(config: dict, split: str) -> dict[str, int]:
    """데이터셋별 유형 수량. 예: training -> {span_extraction: 14000, ...}"""
    size = config["dataset"]["split_sizes"][split]
    ratio = config["dataset"]["type_ratio"]
    counts = {qa_type: round(size * ratio[qa_type]) for qa_type in QA_TYPES}
    if sum(counts.values()) != size:
        raise ValueError(f"{split} 유형별 수량 합계 {sum(counts.values())}가 {size}와 다릅니다. type_ratio를 확인하세요.")
    return counts


def get_yes_count(config: dict, entailment_count: int) -> int:
    """Yes/No 단문형 수량 중 '예'의 수량."""
    return round(entailment_count * config["dataset"]["yes_ratio"])


# ---------------------------------------------------------------------------
# 텍스트 정규화
# ---------------------------------------------------------------------------

# 전각 ASCII(！~～) -> 반각 변환표. 예: ％ -> %, ｍ -> m
_FULLWIDTH_TO_HALFWIDTH = {code: code - 0xFEE0 for code in range(0xFF01, 0xFF5F)}


def normalize_with_map(text: str, remove_symbols: set[str]) -> tuple[str, list[int]]:
    """텍스트를 정규화하고, 정규화된 각 글자가 원본의 몇 번째 글자였는지 함께 돌려준다.

    - 전각 ASCII -> 반각
    - 목록 기호(remove_symbols) 제거
    - 연속 공백은 공백 1개로, 줄바꿈이 섞인 공백은 줄바꿈 1개로
    - 앞뒤 공백 제거
    """
    # 1차: 글자 단위 변환 (공백은 ' ' 또는 '\n'으로 통일)
    chars: list[tuple[str, int]] = []
    for idx, ch in enumerate(text):
        if ch in remove_symbols:
            continue
        ch = chr(_FULLWIDTH_TO_HALFWIDTH.get(ord(ch), ord(ch)))
        if ch in "\r\n":
            ch = "\n"
        elif ch.isspace():
            ch = " "
        chars.append((ch, idx))

    # 2차: 연속 공백 압축
    out_chars: list[str] = []
    out_map: list[int] = []
    i = 0
    while i < len(chars):
        ch, idx = chars[i]
        if ch in " \n":
            j = i
            has_newline = False
            while j < len(chars) and chars[j][0] in " \n":
                has_newline = has_newline or chars[j][0] == "\n"
                j += 1
            out_chars.append("\n" if has_newline else " ")
            out_map.append(idx)
            i = j
        else:
            out_chars.append(ch)
            out_map.append(idx)
            i += 1

    # 앞뒤 공백 제거
    start, end = 0, len(out_chars)
    while start < end and out_chars[start] in " \n":
        start += 1
    while end > start and out_chars[end - 1] in " \n":
        end -= 1
    return "".join(out_chars[start:end]), out_map[start:end]


def normalize_text(text: str, remove_symbols: set[str]) -> str:
    """텍스트 정규화 (본문, 질문, 답, 근거 공통)."""
    return normalize_with_map(text, remove_symbols)[0]


def _find_normalized_start(norm_map: list[int], original_start: int) -> int | None:
    """원본 답 위치(original_start)에 해당하는 정규화 본문의 위치를 찾는다."""
    for norm_idx, orig_idx in enumerate(norm_map):
        if orig_idx >= original_start:
            return norm_idx
    return None


# ---------------------------------------------------------------------------
# 원본 로드 + 정제
# ---------------------------------------------------------------------------

def _load_raw(config: dict, source_split: str, qa_type: str) -> list[dict]:
    with open(get_raw_file(config, source_split, qa_type), encoding="utf-8") as f:
        return json.load(f)["data"]


def _build_record(qa: dict, qa_type: str, context: str, raw_context: str,
                  norm_map: list[int], config: dict) -> tuple[dict | None, str | None]:
    """질문 1개를 출력 레코드로 변환한다. 제외 대상이면 (None, 제외 사유)를 돌려준다."""
    remove_symbols = set(config["normalization"]["remove_symbols"])
    answers_cfg = config["answers"]

    question = normalize_text(qa.get("question") or "", remove_symbols)
    if not question:
        return None, "빈 질문"

    answers = qa.get("answers") or {}
    raw_answer = answers.get("text") or ""
    evidence = answers.get("clue_text")
    evidence = normalize_text(evidence, remove_symbols) if evidence else None

    record = {
        "id": str(qa["question_id"]),
        "question_type": qa_type,
        "question": question,
        "context": context,
        "answer": None,
        "answer_start": None,
        "evidence": evidence or None,
        "is_impossible": False,
    }

    if qa_type == "unanswerable":
        record["answer"] = answers_cfg["unanswerable"]
        record["is_impossible"] = True
        return record, None

    if qa_type == "text_entailment":
        mapping = {"Yes": answers_cfg["yes"], "No": answers_cfg["no"]}
        if raw_answer not in mapping:
            return None, "Yes/No 외 답"
        record["answer"] = mapping[raw_answer]
        return record, None

    # 추출형 / 추론형: 답이 본문 속 구절
    if not raw_answer:
        return None, "빈 답"
    raw_start = answers.get("answer_start")
    # 원본 위치 오류
    if raw_start is None or raw_context[raw_start:raw_start + len(raw_answer)] != raw_answer:
        return None, "answer_start 위치 오류"
    # 정규화 후 위치 재확인
    answer = normalize_text(raw_answer, remove_symbols)
    norm_start = _find_normalized_start(norm_map, raw_start)
    if not answer or norm_start is None or context[norm_start:norm_start + len(answer)] != answer:
        return None, "정규화 후 위치 불일치"
    record["answer"] = answer
    record["answer_start"] = norm_start
    return record, None


def _clean_documents(docs: list[dict], qa_type: str, source_split: str, config: dict,
                     stats: Counter, seen_contexts: set, seen_doc_ids: set) -> list[dict]:
    """원본 기사 목록을 정제해 후보 기사 목록으로 만든다.

    seen_contexts, seen_doc_ids 는 같은 원본(TL 또는 VL)의 모든 유형이 함께 쓰는 집합이다.
    같은 기사가 다른 유형 파일에도 들어 있는 경우가 있어서, 먼저 처리한 유형에만 남긴다.

    후보 기사 = {"context", "metadata", "records": [질문별 레코드]}
    """
    remove_symbols = set(config["normalization"]["remove_symbols"])
    stratify_field = config["dataset"]["golden_stratify_field"]
    candidates = []
    file_contexts = set()

    for doc in docs:
        for paragraph in doc.get("paragraphs", []):
            raw_context = paragraph.get("context") or ""
            qas = paragraph.get("qas", [])
            stats["원본 질문"] += len(qas)

            context, norm_map = normalize_with_map(raw_context, remove_symbols)
            if not context:
                stats["제외: 빈 본문"] += len(qas)
                continue

            records = []
            for qa in qas:
                record, reason = _build_record(qa, qa_type, context, raw_context, norm_map, config)
                if record is None:
                    stats[f"제외: {reason}"] += 1
                else:
                    records.append(record)
            if not records:
                continue

            # 같은 본문은 1건만 남김 (완전 중복 포함)
            if context in file_contexts:
                stats["제외: 중복 본문"] += len(records)
                continue
            file_contexts.add(context)
            # 앞서 처리한 다른 유형에 같은 기사가 있으면 제외
            if context in seen_contexts or doc.get("doc_id") in seen_doc_ids:
                stats["제외: 다른 유형과 같은 기사"] += len(records)
                continue
            seen_contexts.add(context)
            seen_doc_ids.add(doc.get("doc_id"))

            candidates.append({
                "context": context,
                "metadata": {
                    "doc_id": doc.get("doc_id"),
                    "doc_title": doc.get("doc_title"),
                    "source": doc.get("doc_source"),
                    "published": doc.get("doc_published"),
                    "category": (doc.get("doc_class") or {}).get(stratify_field),
                    "source_split": SOURCE_SPLITS[source_split]["prefix"],
                },
                "records": records,
            })

    stats["정제 후 기사"] = len(candidates)
    return candidates


def _pick_questions(candidates: list[dict], per_doc: int, rng: random.Random) -> list[dict]:
    """기사마다 질문을 per_doc개만 골라 최종 레코드 목록으로 만든다."""
    picked = []
    for cand in candidates:
        for record in rng.sample(cand["records"], min(per_doc, len(cand["records"]))):
            picked.append({**record, "metadata": dict(cand["metadata"])})
    return picked


# ---------------------------------------------------------------------------
# 샘플링
# ---------------------------------------------------------------------------

def _rng(config: dict, *keys: str) -> random.Random:
    """단계별로 독립된 난수 생성기. 한 단계를 바꿔도 다른 단계 결과가 흔들리지 않는다."""
    return random.Random("-".join([str(config["dataset"]["random_seed"]), *keys]))


def _sample(pool: list[dict], count: int, rng: random.Random, label: str) -> list[dict]:
    if len(pool) < count:
        raise ValueError(f"{label}: 후보 {len(pool)}건으로 {count}건을 뽑을 수 없습니다.")
    return rng.sample(pool, count)


def _sample_stratified(pool: list[dict], count: int, rng: random.Random, label: str) -> list[dict]:
    """분야(category)별로 돌아가며 1건씩 뽑아 분야가 고르게 섞이도록 한다."""
    if len(pool) < count:
        raise ValueError(f"{label}: 후보 {len(pool)}건으로 {count}건을 뽑을 수 없습니다.")
    by_category = defaultdict(list)
    for record in pool:
        by_category[record["metadata"]["category"]].append(record)
    categories = sorted(by_category, key=str)
    for cat in categories:
        rng.shuffle(by_category[cat])
    rng.shuffle(categories)

    picked = []
    while len(picked) < count:
        for cat in categories:
            if by_category[cat] and len(picked) < count:
                picked.append(by_category[cat].pop())
    return picked


def _sample_type(pool: list[dict], qa_type: str, count: int, config: dict,
                 rng: random.Random, stratified: bool, label: str) -> list[dict]:
    """유형 1개에서 count건을 뽑는다. Yes/No 단문형은 yes_ratio에 맞춰 나눠 뽑는다."""
    sampler = _sample_stratified if stratified else _sample
    if qa_type != "text_entailment":
        return sampler(pool, count, rng, label)

    yes_answer, no_answer = config["answers"]["yes"], config["answers"]["no"]
    yes_count = get_yes_count(config, count)
    yes_pool = [r for r in pool if r["answer"] == yes_answer]
    no_pool = [r for r in pool if r["answer"] == no_answer]
    return (sampler(yes_pool, yes_count, rng, f"{label}(예)")
            + sampler(no_pool, count - yes_count, rng, f"{label}(아니오)"))


def group_key(record: dict) -> str:
    """구간 배치·검증에 쓰는 그룹. Yes/No 단문형은 예/아니오를 따로 본다."""
    if record["question_type"] == "text_entailment":
        return f"text_entailment:{record['answer']}"
    return record["question_type"]


def order_by_chunks(records: list[dict], rng: random.Random) -> list[dict]:
    """어느 chunk_size 구간을 잘라도 그룹(유형, 예/아니오) 비율이 같도록 순서를 배치한다.

    그룹마다 레코드를 섞은 뒤 j번째 레코드에 위치값 (j + 0.5) / 그룹 크기 를 주고,
    전체를 위치값 순으로 정렬한다. 그러면 각 그룹이 전체 순서에 고르게 퍼진다.
    (전체 크기와 그룹 크기가 구간 수로 나눠떨어지면 구간마다 정확히 같은 수량이 들어간다)
    """
    groups = defaultdict(list)
    for record in records:
        groups[group_key(record)].append(record)

    keyed = []
    for key in sorted(groups):
        members = groups[key]
        rng.shuffle(members)
        n = len(members)
        for j, record in enumerate(members):
            keyed.append(((j + 0.5) / n, rng.random(), record))
    keyed.sort(key=lambda item: (item[0], item[1]))
    return [record for _, _, record in keyed]


# ---------------------------------------------------------------------------
# 전체 실행
# ---------------------------------------------------------------------------

def _print_stats(title: str, stats: Counter) -> None:
    print(f"  [{title}]")
    for key, value in stats.items():
        print(f"    {key}: {value:,}")


def prepare_datasets(config: dict) -> dict[str, list[dict]]:
    """원본을 정제·샘플링해 {training, validation, golden} 레코드 목록을 만든다."""
    per_doc = config["dataset"]["questions_per_doc"]
    pools = {"training": {}, "validation": {}}
    validation_contexts, validation_doc_ids = set(), set()

    # 1~4. 로드 + 정제 + 기사당 질문 선택 (VL을 먼저 처리해 겹침 확인에 사용)
    for source_split in ("validation", "training"):
        print(f"\n== 원본 {source_split} ({SOURCE_SPLITS[source_split]['prefix']}) 정제")
        seen_contexts, seen_doc_ids = set(), set()
        for qa_type in CLEANING_ORDER:
            stats = Counter()
            docs = _load_raw(config, source_split, qa_type)
            stats["원본 기사"] = len(docs)
            candidates = _clean_documents(docs, qa_type, source_split, config, stats,
                                          seen_contexts, seen_doc_ids)
            del docs

            if source_split == "validation":
                validation_contexts.update(c["context"] for c in candidates)
                validation_doc_ids.update(c["metadata"]["doc_id"] for c in candidates)
            else:
                before = len(candidates)
                candidates = [c for c in candidates
                              if c["context"] not in validation_contexts
                              and c["metadata"]["doc_id"] not in validation_doc_ids]
                stats["제외: Validation 원본과 겹침(기사)"] = before - len(candidates)

            pools[source_split][qa_type] = _pick_questions(
                candidates, per_doc, _rng(config, "pick", source_split, qa_type))
            stats["최종 후보(기사당 질문 1개)"] = len(pools[source_split][qa_type])
            _print_stats(QA_TYPE_LABELS[qa_type], stats)

    # 5. 샘플링
    datasets = {"training": [], "validation": [], "golden": []}

    for qa_type, count in get_type_counts(config, "training").items():
        datasets["training"] += _sample_type(
            pools["training"][qa_type], qa_type, count, config,
            _rng(config, "training", qa_type), stratified=False, label=f"training/{qa_type}")

    # Golden을 먼저 분야별 균등으로 뽑고, 남은 후보에서 Validation을 뽑는다
    golden_counts = get_type_counts(config, "golden")
    validation_counts = get_type_counts(config, "validation")
    for qa_type in QA_TYPES:
        pool = pools["validation"][qa_type]
        golden = _sample_type(pool, qa_type, golden_counts[qa_type], config,
                              _rng(config, "golden", qa_type), stratified=True, label=f"golden/{qa_type}")
        golden_ids = {r["id"] for r in golden}
        remaining = [r for r in pool if r["id"] not in golden_ids]
        datasets["golden"] += golden
        datasets["validation"] += _sample_type(
            remaining, qa_type, validation_counts[qa_type], config,
            _rng(config, "validation", qa_type), stratified=False, label=f"validation/{qa_type}")

    # 6. 순서 배치: Training은 구간별 비율 균일, 나머지는 섞기
    datasets["training"] = order_by_chunks(datasets["training"], _rng(config, "order", "training"))
    for split in ("validation", "golden"):
        _rng(config, "shuffle", split).shuffle(datasets[split])
    return datasets


def save_datasets(config: dict, datasets: dict[str, list[dict]]) -> None:
    print("\n== 저장")
    for split, records in datasets.items():
        path = get_output_file(config, split)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        type_counts = Counter(QA_TYPE_LABELS[r["question_type"]] for r in records)
        print(f"  {split}: {len(records):,}건 -> {path}")
        print(f"    유형별: {dict(type_counts)}")


def main() -> None:
    config = load_config()
    datasets = prepare_datasets(config)
    save_datasets(config, datasets)


if __name__ == "__main__":
    main()
