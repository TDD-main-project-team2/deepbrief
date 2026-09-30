import json
from pathlib import Path

import torch
import yaml
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from trl import SFTConfig, SFTTrainer

BASE_DIR = Path(__file__).resolve().parent

DTYPE_MAP = {
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
    "float32": torch.float32,
}


def load_config():
    with (BASE_DIR / "config.yaml").open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_dataset_file(relative_path, sample_limit=None):
    data_path = BASE_DIR / relative_path
    with data_path.open(encoding="utf-8") as file:
        data = json.load(file)

    if sample_limit is not None:
        if type(sample_limit) is not int or sample_limit < 1:
            raise ValueError("sample_limit은 양의 정수 또는 null이어야 합니다.")
        data = data[:sample_limit]

    dataset = Dataset.from_list(data)

    return dataset


def load_training_data(config):
    data_config = config["data"]
    train_dataset = load_dataset_file(
        data_config["train_path"], data_config["sample_limit"]
    )
    validation_dataset = load_dataset_file(
        data_config["validation_path"], data_config["validation_sample_limit"]
    )

    return train_dataset, validation_dataset


def build_quantization_config(config):
    quantization = config["quantization"]
    return BitsAndBytesConfig(
        load_in_4bit=quantization["load_in_4bit"],
        bnb_4bit_quant_type=quantization["quant_type"],
        bnb_4bit_use_double_quant=quantization["double_quant"],
        bnb_4bit_compute_dtype=DTYPE_MAP[quantization["compute_dtype"]],
    )


def apply_qlora(model, config):
    lora = config["lora"]
    lora_config = LoraConfig(
        r=lora["rank"],
        lora_alpha=lora["alpha"],
        target_modules=lora["target_modules"],
        lora_dropout=lora["dropout"],
        bias=lora["bias"],
        task_type=TaskType.CAUSAL_LM,
    )

    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=config["training"]["gradient_checkpointing"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    model.config.use_cache = False

    return model


def load_model_and_tokenizer(config):
    model_name = config["model"]["name"]
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=build_quantization_config(config),
        device_map="auto",
        dtype=DTYPE_MAP[config["model"]["dtype"]],
    )
    model = apply_qlora(model, config)

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return model, tokenizer


def build_summary_messages(passage):
    """원문 텍스트에 요약 지시문을 붙여 user 메시지 리스트를 반환한다."""

    return [
        {
            "role": "user",
            "content": (
                "다음 원문의 핵심 내용을 한국어로 간결하게 요약하세요. "
                "원문에 없는 사실은 추가하지 마세요.\n\n"
                f"### 원문 텍스트:\n{passage}"
            ),
        }
    ]


def build_training_messages(example):
    """데이터 한 건에서 원문과 정답 요약을 읽어 학습용 메시지를 반환한다."""

    passage = example["Meta(Refine)"]["passage"]
    summary = example["Annotation"]["summary3"]

    if not isinstance(passage, str) or not passage.strip():
        raise ValueError("학습 원문 passage가 비어 있거나 문자열이 아닙니다.")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("정답 요약 summary3가 비어 있거나 문자열이 아닙니다.")

    return build_summary_messages(passage) + [{"role": "assistant", "content": summary}]


def format_training_example(example):
    """SFTTrainer가 토큰화할 원문과 정답 메시지를 분리한다."""
    messages = build_training_messages(example)
    return {"prompt": messages[:-1], "completion": messages[-1:]}


def prepare_training_dataset(dataset):
    return dataset.map(
        format_training_example,
        batched=False,
        remove_columns=dataset.column_names,
    )


def train_and_save(model, tokenizer, train_dataset, validation_dataset, config):
    training_config = config["training"]
    evaluation_config = config["evaluation"]
    output_dir = BASE_DIR / training_config["output_dir"]

    training_args = SFTConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=training_config["batch_size"],
        gradient_accumulation_steps=training_config["gradient_accumulation_steps"],
        learning_rate=training_config["learning_rate"],
        num_train_epochs=training_config["epochs"],
        max_steps=training_config["max_steps"],
        logging_steps=training_config["logging_steps"],
        save_strategy=training_config["save_strategy"],
        eval_strategy=evaluation_config["strategy"],
        eval_steps=evaluation_config["eval_steps"],
        load_best_model_at_end=evaluation_config["load_best_model_at_end"],
        metric_for_best_model=evaluation_config["metric_for_best_model"],
        greater_is_better=evaluation_config["greater_is_better"],
        save_total_limit=training_config["save_total_limit"],
        optim=training_config["optim"],
        gradient_checkpointing=training_config["gradient_checkpointing"],
        dataloader_pin_memory=training_config["dataloader_pin_memory"],
        report_to=training_config["report_to"],
        max_length=config["data"]["max_sequence_length"],
        completion_only_loss=True,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        processing_class=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
    )

    trainer.train()

    trainer.save_model(str(output_dir / "final-adapter"))  # 어댑터 저장
    tokenizer.save_pretrained(str(output_dir / "final-adapter"))  # 토크나이저 저장
    print(f"어댑터 저장 완료: {output_dir / 'final-adapter'}")


def main():
    config = load_config()
    dataset, validation_dataset = load_training_data(config)
    train_dataset = prepare_training_dataset(dataset)
    validation_dataset = prepare_training_dataset(validation_dataset)
    model, tokenizer = load_model_and_tokenizer(config)
    train_and_save(model, tokenizer, train_dataset, validation_dataset, config)


if __name__ == "__main__":
    main()
