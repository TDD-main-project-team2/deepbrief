"""
QA 파인튜닝 데이터셋 검증 (형식 + 품질)

data_preparation.py가 만든 Training / Validation / Golden 데이터셋을 검사한다.
기준값(수량, 비율, 답 문구, 제거 기호)은 config.yaml 에서 읽는다.

실행 (레포 루트에서)
    python backend/fine_tuning/qa/data_validation.py             # 검증
    python backend/fine_tuning/qa/data_validation.py --sample 5  # 검증 + 표본 검수용 출력 (유형별 5건)

검사 항목
    오류 (하나라도 있으면 실패, 종료 코드 1)
        1. 파일 형식       : 파일이 있고 JSON 배열인지
        2. 필수 필드·타입  : 필드 존재, 타입, 빈 문자열 여부
        3. 유형별 규칙     : 답 위치 / 예·아니오 / 응답불가 문구
        4. 수량·비율       : config.yaml 설정과 일치하는지
        5. 파일 내 중복    : id, 본문
        6. 데이터셋 간 겹침: id, doc_id, 본문 + Golden 검수 제외 id 미포함
        7. 출처            : training은 TL, validation·golden은 VL
        8. 정규화          : 제거 대상 기호, 전각 문자, 연속 공백
        9. 구간 구성       : training의 chunk_size 구간마다 유형·예/아니오 수량이 같은지 (허용 오차 ±1)
    경고 (확인용 출력)
       10. 길이 이상치     : IQR 기준으로 크게 벗어난 본문·질문·답 길이
       11. 분포            : 분야(category) 분포
"""

import argparse
import json
import random
import statistics
import sys
from collections import Counter, defaultdict

try:
    from .data_preparation import (
        QA_TYPE_LABELS,
        QA_TYPES,
        SOURCE_SPLITS,
        SPLIT_SOURCES,
        get_output_file,
        get_type_counts,
        get_yes_count,
        group_key,
        load_config,
    )
except ImportError:
    from data_preparation import (
        QA_TYPE_LABELS,
        QA_TYPES,
        SOURCE_SPLITS,
        SPLIT_SOURCES,
        get_output_file,
        get_type_counts,
        get_yes_count,
        group_key,
        load_config,
    )


SPLITS = ("training", "validation", "golden")

# 필수 필드와 허용 타입
REQUIRED_FIELDS = {
    "id": (str,),
    "question_type": (str,),
    "question": (str,),
    "context": (str,),
    "answer": (str,),
    "answer_start": (int, type(None)),
    "evidence": (str, type(None)),
    "is_impossible": (bool,),
    "metadata": (dict,),
}
REQUIRED_METADATA = ("doc_id", "doc_title", "source", "published", "category", "source_split")

# 데이터셋별 허용 출처
EXPECTED_SOURCE = {split: SOURCE_SPLITS[source]["prefix"] for split, source in SPLIT_SOURCES.items()}

# 정규화 검사 대상 필드
TEXT_FIELDS = ("question", "context", "answer", "evidence")

# 오류 검사 항목 (출력 순서)
CHECK_NAMES = (
    "1. 파일 형식",
    "2. 필수 필드·타입",
    "3. 유형별 규칙",
    "4. 수량·비율",
    "5. 파일 내 중복",
    "6. 데이터셋 간 겹침",
    "7. 출처",
    "8. 정규화",
    "9. 구간 구성",
)

# 실패 항목마다 보여줄 예시 수
MAX_EXAMPLES = 5


class Report:
    """검사 결과를 항목별로 모은다."""

    def __init__(self) -> None:
        self.errors: dict[str, list[str]] = defaultdict(list)
        self.warnings: dict[str, list[str]] = defaultdict(list)

    def error(self, name: str, message: str) -> None:
        self.errors[name].append(message)

    def warn(self, name: str, message: str) -> None:
        self.warnings[name].append(message)

    def print(self) -> None:
        print("\n== 검증 결과 (오류)")
        for name in CHECK_NAMES:
            problems = self.errors.get(name, [])
            status = "통과" if not problems else f"실패 {len(problems):,}건"
            print(f"  [{status}] {name}")
            for message in problems[:MAX_EXAMPLES]:
                print(f"      - {message}")
            if len(problems) > MAX_EXAMPLES:
                print(f"      ... 외 {len(problems) - MAX_EXAMPLES:,}건")

        print("\n== 확인 사항 (경고)")
        for name, messages in self.warnings.items():
            print(f"  [{name}]")
            for message in messages:
                print(f"      {message}")

        total = sum(len(v) for v in self.errors.values())
        print("\n== 최종:", "통과" if total == 0 else f"실패 (오류 {total:,}건)")


# ---------------------------------------------------------------------------
# 1. 파일 형식
# ---------------------------------------------------------------------------

def load_datasets(config: dict, report: Report) -> dict[str, list[dict]]:
    name = "1. 파일 형식"
    datasets = {}
    for split in SPLITS:
        path = get_output_file(config, split)
        if not path.exists() or path.stat().st_size == 0:
            report.error(name, f"{split}: 파일이 없거나 비어 있음 ({path})")
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            report.error(name, f"{split}: JSON 파싱 실패 ({e})")
            continue
        if not isinstance(data, list):
            report.error(name, f"{split}: 최상위가 배열이 아님")
            continue
        datasets[split] = data
    return datasets


# ---------------------------------------------------------------------------
# 2~3. 레코드 단위 검사
# ---------------------------------------------------------------------------

def check_fields(split: str, records: list, report: Report) -> list[dict]:
    """필수 필드·타입 검사. 통과한 레코드만 돌려준다 (이후 검사는 형식이 맞다는 전제)."""
    name = "2. 필수 필드·타입"
    valid = []
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            report.error(name, f"{split} #{i}: 레코드가 객체가 아님")
            continue
        rid = record.get("id", f"#{i}")
        problems = []
        for field, types in REQUIRED_FIELDS.items():
            value = record.get(field)
            if field not in record:
                problems.append(f"{field} 없음")
            # bool은 int의 하위 타입이라 answer_start에 true/false가 들어가는 경우를 따로 막는다
            elif not isinstance(value, types) or (int in types and isinstance(value, bool)):
                problems.append(f"{field} 타입 오류")
            elif isinstance(value, str) and not value.strip():
                problems.append(f"{field} 빈 문자열")
        if isinstance(record.get("metadata"), dict):
            for key in REQUIRED_METADATA:
                if key not in record["metadata"]:
                    problems.append(f"metadata.{key} 없음")
        if record.get("question_type") not in QA_TYPES:
            problems.append(f"알 수 없는 question_type: {record.get('question_type')}")
        if problems:
            report.error(name, f"{split} {rid}: {', '.join(problems)}")
        else:
            valid.append(record)
    return valid


def check_type_rules(split: str, records: list[dict], config: dict, report: Report) -> None:
    name = "3. 유형별 규칙"
    answers = config["answers"]
    for r in records:
        qa_type, rid = r["question_type"], r["id"]
        if qa_type in ("span_extraction", "span_inference"):
            start = r["answer_start"]
            if start is None or r["context"][start:start + len(r["answer"])] != r["answer"]:
                report.error(name, f"{split} {rid}: answer_start 위치에 답이 없음")
            if r["is_impossible"]:
                report.error(name, f"{split} {rid}: {qa_type}인데 is_impossible=true")
        elif qa_type == "text_entailment":
            if r["answer"] not in (answers["yes"], answers["no"]):
                report.error(name, f"{split} {rid}: 답이 예/아니오가 아님 ({r['answer']})")
            if r["answer_start"] is not None or r["is_impossible"]:
                report.error(name, f"{split} {rid}: Yes/No형은 answer_start=null, is_impossible=false여야 함")
        elif qa_type == "unanswerable":
            if r["answer"] != answers["unanswerable"]:
                report.error(name, f"{split} {rid}: 응답불가 문구가 아님")
            if r["answer_start"] is not None or not r["is_impossible"]:
                report.error(name, f"{split} {rid}: 응답불가형은 answer_start=null, is_impossible=true여야 함")


# ---------------------------------------------------------------------------
# 4~9. 데이터셋 단위 검사
# ---------------------------------------------------------------------------

def check_counts(split: str, records: list[dict], config: dict, report: Report) -> None:
    name = "4. 수량·비율"
    expected_total = config["dataset"]["split_sizes"][split]
    if len(records) != expected_total:
        report.error(name, f"{split}: 전체 {len(records):,}건 (기대 {expected_total:,}건)")

    expected_types = get_type_counts(config, split)
    type_counts = Counter(r["question_type"] for r in records)
    for qa_type, expected in expected_types.items():
        if type_counts[qa_type] != expected:
            report.error(name, f"{split}: {QA_TYPE_LABELS[qa_type]} {type_counts[qa_type]:,}건 (기대 {expected:,}건)")

    expected_yes = get_yes_count(config, expected_types["text_entailment"])
    actual_yes = sum(1 for r in records
                     if r["question_type"] == "text_entailment" and r["answer"] == config["answers"]["yes"])
    if actual_yes != expected_yes:
        report.error(name, f"{split}: Yes/No형 '예' {actual_yes}건 (기대 {expected_yes}건)")


def check_duplicates(split: str, records: list[dict], report: Report) -> None:
    name = "5. 파일 내 중복"
    for field, getter in (("id", lambda r: r["id"]), ("본문", lambda r: r["context"])):
        counts = Counter(getter(r) for r in records)
        for r in records:
            if counts[getter(r)] > 1:
                report.error(name, f"{split} {r['id']}: {field} 중복")


def check_overlap(datasets: dict[str, list[dict]], report: Report) -> None:
    name = "6. 데이터셋 간 겹침"
    keys = {
        "id": lambda r: r["id"],
        "doc_id": lambda r: r["metadata"]["doc_id"],
        "본문": lambda r: r["context"],
    }
    splits = [s for s in SPLITS if s in datasets]
    for i, a in enumerate(splits):
        for b in splits[i + 1:]:
            for field, getter in keys.items():
                overlap = {getter(r) for r in datasets[a]} & {getter(r) for r in datasets[b]}
                if overlap:
                    report.error(name, f"{a} - {b}: {field} {len(overlap):,}건 겹침")


def check_excluded(datasets: dict[str, list[dict]], config: dict, report: Report) -> None:
    """Golden 검수에서 제외한 id가 어느 데이터셋에도 남아 있지 않은지 본다."""
    name = "6. 데이터셋 간 겹침"
    exclude_ids = {str(i) for i in (config["dataset"].get("golden_exclude_ids") or [])}
    for split, records in datasets.items():
        for r in records:
            if r["id"] in exclude_ids:
                report.error(name, f"{split} {r['id']}: 검수 제외 id가 포함됨")


def check_source(split: str, records: list[dict], report: Report) -> None:
    name = "7. 출처"
    for r in records:
        if r["metadata"]["source_split"] != EXPECTED_SOURCE[split]:
            report.error(name, f"{split} {r['id']}: 출처 {r['metadata']['source_split']} (기대 {EXPECTED_SOURCE[split]})")


def _normalization_problems(text: str, remove_symbols: set[str]) -> list[str]:
    problems = []
    if any(ch in remove_symbols for ch in text):
        problems.append("제거 대상 기호")
    if any(0xFF01 <= ord(ch) <= 0xFF5E for ch in text):
        problems.append("전각 문자")
    if any(p in text for p in ("  ", "\n\n", " \n", "\n ", "\r", "\t")):
        problems.append("연속 공백/줄바꿈")
    if text != text.strip():
        problems.append("앞뒤 공백")
    return problems


def check_normalization(split: str, records: list[dict], config: dict, report: Report) -> None:
    name = "8. 정규화"
    remove_symbols = set(config["normalization"]["remove_symbols"])
    for r in records:
        for field in TEXT_FIELDS:
            if r[field] is None:
                continue
            problems = _normalization_problems(r[field], remove_symbols)
            if problems:
                report.error(name, f"{split} {r['id']}: {field} - {', '.join(problems)}")


def check_chunks(records: list[dict], config: dict, report: Report) -> None:
    """training을 chunk_size씩 잘랐을 때 구간마다 그룹(유형, 예/아니오) 수량이 기대값과 같은지 본다."""
    name = "9. 구간 구성"
    chunk_size = config["dataset"]["chunk_size"]
    total = len(records)
    totals = Counter(group_key(r) for r in records)
    for start in range(0, total, chunk_size):
        chunk = records[start:start + chunk_size]
        counts = Counter(group_key(r) for r in chunk)
        chunk_no = start // chunk_size + 1
        for key, group_total in totals.items():
            expected = group_total * len(chunk) / total
            if abs(counts[key] - expected) > 1:
                report.error(name, f"training 구간 {chunk_no}: {key} {counts[key]}건 (기대 약 {expected:.0f}건)")


# ---------------------------------------------------------------------------
# 10~11. 경고
# ---------------------------------------------------------------------------

def check_lengths(split: str, records: list[dict], report: Report) -> None:
    """IQR 기준 길이 이상치. 사분위 범위(Q3-Q1)의 1.5배를 벗어나면 이상치로 센다."""
    name = f"10. 길이 이상치 ({split})"
    targets = {
        "본문": [len(r["context"]) for r in records],
        "질문": [len(r["question"]) for r in records],
        # 답 길이는 본문 속 구절인 유형만 의미가 있음
        "답(추출·추론형)": [len(r["answer"]) for r in records
                        if r["question_type"] in ("span_extraction", "span_inference")],
    }
    for label, lengths in targets.items():
        if len(lengths) < 4:
            continue
        q1, _, q3 = statistics.quantiles(lengths, n=4)
        low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        outliers = sum(1 for n in lengths if n < low or n > high)
        report.warn(name, f"{label}: 최소 {min(lengths)} / 평균 {statistics.mean(lengths):.0f} / "
                          f"최대 {max(lengths)}자, 이상치 {outliers}건 (정상 범위 {max(low, 0):.0f}~{high:.0f}자)")


def check_distribution(split: str, records: list[dict], report: Report) -> None:
    name = f"11. 분야 분포 ({split})"
    counts = Counter(r["metadata"]["category"] for r in records)
    report.warn(name, ", ".join(f"{k} {v}" for k, v in counts.most_common()))


# ---------------------------------------------------------------------------
# 표본 검수 출력
# ---------------------------------------------------------------------------

# 표본 출력에서 보여줄 본문 길이
PREVIEW_HEAD = 300    # 답 위치가 없는 유형: 본문 앞부분 글자 수
PREVIEW_AROUND = 150  # 답 위치가 있는 유형: 답 앞뒤로 보여줄 글자 수


def _context_preview(record: dict) -> str:
    """표본 출력용 본문 일부.

    추출형·추론형은 답 주변 구간을 보여주고 답을 [[ ]]로 표시한다.
    Yes/No형·응답불가형은 답 위치가 없으므로 본문 앞부분을 보여준다.
    """
    context, start = record["context"], record["answer_start"]
    if start is None:
        return context[:PREVIEW_HEAD] + (" ..." if len(context) > PREVIEW_HEAD else "")
    end = start + len(record["answer"])
    left, right = max(0, start - PREVIEW_AROUND), min(len(context), end + PREVIEW_AROUND)
    return ("... " if left > 0 else "") + context[left:start] + "[[" + context[start:end] + "]]" \
        + context[end:right] + (" ..." if right < len(context) else "")


def print_samples(datasets: dict[str, list[dict]], config: dict, per_type: int) -> None:
    print(f"\n== 표본 검수용 출력 (데이터셋·유형별 {per_type}건)")
    seed = config["dataset"]["random_seed"]
    for split, records in datasets.items():
        by_type = defaultdict(list)
        for r in records:
            by_type[r["question_type"]].append(r)
        for qa_type in QA_TYPES:
            pool = by_type.get(qa_type, [])
            rng = random.Random(f"{seed}-review-{split}-{qa_type}")
            for r in rng.sample(pool, min(per_type, len(pool))):
                print(f"\n--- [{split} / {QA_TYPE_LABELS[qa_type]}] id={r['id']}")
                print(f"질문: {r['question']}")
                print(f"답  : {r['answer']}")
                if r.get("evidence"):
                    print(f"근거: {r['evidence']}")
                print(f"본문: {_context_preview(r)}")


# ---------------------------------------------------------------------------
# 전체 실행
# ---------------------------------------------------------------------------

def validate(sample: int = 0) -> bool:
    """전체 검증을 실행하고 결과를 출력한다. 오류가 없으면 True."""
    config = load_config()
    report = Report()
    datasets = load_datasets(config, report)

    valid_datasets = {}
    for split, records in datasets.items():
        valid = check_fields(split, records, report)
        valid_datasets[split] = valid
        check_type_rules(split, valid, config, report)
        check_counts(split, valid, config, report)
        check_duplicates(split, valid, report)
        check_source(split, valid, report)
        check_normalization(split, valid, config, report)
        if split == "training":
            check_chunks(valid, config, report)
        check_lengths(split, valid, report)
        check_distribution(split, valid, report)
    check_overlap(valid_datasets, report)
    check_excluded(valid_datasets, config, report)

    report.print()
    if sample > 0:
        print_samples(valid_datasets, config, sample)
    return not report.errors


def main() -> None:
    parser = argparse.ArgumentParser(description="QA 파인튜닝 데이터셋 검증")
    parser.add_argument("--sample", type=int, default=0,
                        help="표본 검수용으로 데이터셋·유형별 N건 출력 (기본 0: 출력 안 함)")
    args = parser.parse_args()
    sys.exit(0 if validate(args.sample) else 1)


if __name__ == "__main__":
    main()
