import json
import random
from pathlib import Path


def combine_and_clean(
    root: Path,
    target_folder: Path,
    output_file: Path
):
    combined = []

    for file in root.rglob("*.json"):

        try:
            file.relative_to(root / target_folder)
            
        except ValueError:
            continue

        if file.resolve() == output_file.resolve():
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            print(f"Skipping {file}: {e}")
            continue

        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = [data]
        else:
            continue

        # summary1 summary2 제외
        for item in records:
            if not isinstance(item, dict):
                continue

            annotation = item.get("Annotation")

            if isinstance(annotation, dict):
                annotation.pop("summary1", None)
                annotation.pop("summary2", None)

        combined.extend(records)


    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"총 {len(combined):,} records")
    print(f"Saved to: {output_file}")

def extract_required(input_file: Path, output_file: Path, required_num: int):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    selected = random.sample(data, required_num)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    print(f"Selected {len(selected):,} records")
    print(f"Saved to: {output_file}")

    return selected

def extract_golden_dataset(
    input_file: Path,
    training_data,
    output_file: Path,
    required_num: int
):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    remaining = [
        item for item in data
        if item not in training_data
    ]

    selected = random.sample(remaining, required_num)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    print(f"Selected {len(selected):,} golden records")
    print(f"Saved to: {output_file}")

def validate_no_overlap(training_file: Path, golden_file: Path):
    with open(training_file, "r", encoding="utf-8") as f:
        training_data = json.load(f)

    with open(golden_file, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    training_set = {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in training_data}
    golden_set = {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in golden_data}

    overlap = training_set & golden_set

    if overlap:
        print(f"❌ WARNING: {len(overlap):,} 중복 데이터 발견")
    else:
        print("✅ 중복 없습니다.")

def main():
    root = Path("backend")

    combine_and_clean(
        root=root,
        target_folder=Path("fine_tuning/summary/data/raw/training"),
        output_file=root / "fine_tuning/summary/data/raw/training/summary_training.json"
    )

    combine_and_clean(
        root=root,
        target_folder=Path("fine_tuning/summary/data/raw/validation"),
        output_file=root / "fine_tuning/summary/data/raw/validation/summary_validation.json"
    )

    training_data = extract_required(
        input_file=root / "fine_tuning/summary/data/raw/training/summary_training.json",
        output_file=root / "fine_tuning/summary/data/processed/training_dataset.json",
        required_num=20000
    )

    extract_golden_dataset(
        input_file=root / "fine_tuning/summary/data/raw/training/summary_training.json",
        training_data=training_data,
        output_file=root / "fine_tuning/summary/data/processed/golden_dataset.json",
        required_num=400
    )

    extract_required(
        input_file=root / "fine_tuning/summary/data/raw/validation/summary_validation.json",
        output_file=root / "fine_tuning/summary/data/processed/validation_dataset.json",
        required_num=2000
    )

    validate_no_overlap(
        training_file=root / "fine_tuning/summary/data/processed/training_dataset.json",
        golden_file=root / "fine_tuning/summary/data/processed/golden_dataset.json"
    )

if __name__ == "__main__":
    main()