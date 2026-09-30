from pathlib import Path
import json
import random
import yaml
from transformers import AutoTokenizer

def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config

def combine_and_clean(
    target_folder: Path,
    output_file: Path
):
    combined = []
    for file in target_folder.rglob("*.json"):
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

def check_token_lengths(
    input_file: Path,
    model_name: str,
    max_seq_length: int
):
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    article_lengths = []
    summary_lengths = []
    total_lengths = []

    for item in data:
        article = item["Meta(Refine)"]["passage"]
        summary = item["Annotation"]["summary3"]

        article_tokens = len(tokenizer.encode(article))
        summary_tokens = len(tokenizer.encode(summary))

        total_tokens = len(
            tokenizer.apply_chat_template(
                [
                    {
                        "role": "user",
                        "content": f"다음 기사를 요약해주세요.\n\n{article}"
                    },
                    {
                        "role": "assistant",
                        "content": summary
                    }
                ],
                tokenize=True,
                add_generation_prompt=False
            )
        )

        article_lengths.append(article_tokens)
        summary_lengths.append(summary_tokens)
        total_lengths.append(total_tokens)

    total = len(total_lengths)
    over_limit = sum(x > max_seq_length for x in total_lengths)

    print("\n=== Token Length Analysis ===")

    print("\nArticles")
    print(f"  Max:     {max(article_lengths):,}")
    print(f"  Average: {sum(article_lengths) / total:,.1f}")

    print("\nSummaries")
    print(f"  Max:     {max(summary_lengths):,}")
    print(f"  Average: {sum(summary_lengths) / total:,.1f}")

    print("\nFull Training Sequence")
    print(f"  Max:     {max(total_lengths):,}")
    print(f"  Average: {sum(total_lengths) / total:,.1f}")

    print(f"\nOver {max_seq_length} tokens:")
    print(f"  {over_limit:,} / {total:,}")
    print(f"  {(over_limit / total) * 100:.2f}%")

def main():
    config = load_config()
    base_dir = Path(__file__).parent

    if not config["data_prep"]["combine_clean_train_complete"]:
        combine_and_clean(
            target_folder=base_dir / config["dataset"]["raw_train_folder"],
            output_file=base_dir / config["dataset"]["raw_combined_train_path"]
        )
    if not config["data_prep"]["combine_clean_validation_complete"]:
        combine_and_clean(
            target_folder=base_dir / config["dataset"]["raw_validation_folder"],
            output_file=base_dir / config["dataset"]["raw_combined_validation_path"]
        )

    if not config["data_prep"]["extract_required_train_and_golden_complete"]:
        training_data = extract_required(
            input_file=base_dir / config["dataset"]["raw_combined_train_path"],
            output_file=base_dir / config["dataset"]["train_path"],
            required_num=config["dataset"]["train_size"]
        )
        extract_golden_dataset(
            input_file=base_dir / config["dataset"]["raw_combined_train_path"],
            training_data=training_data,
            output_file=base_dir / config["dataset"]["golden_path"],
            required_num=config["dataset"]["golden_size"]
        )

    if not config["data_prep"]["extract_required_validation_complete"]:
        extract_required(
            input_file=base_dir / config["dataset"]["raw_combined_validation_path"],
            output_file=base_dir / config["dataset"]["validation_path"],
            required_num=config["dataset"]["validation_size"]
        )

    validate_no_overlap(
        training_file=base_dir / config["dataset"]["train_path"],
        golden_file=base_dir / config["dataset"]["golden_path"]
    )

    check_token_lengths(
        input_file=base_dir / config["dataset"]["train_path"],
        model_name=config["model"]["name"],
        max_seq_length=config["model"]["max_seq_length"]
    )

if __name__ == "__main__":
    main()