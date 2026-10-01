import json
from pathlib import Path

import torch
import yaml
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
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
        data = data[:sample_limit]

    return Dataset.from_list(data)

def load_datasets(config):
    max_train_samples = config["training"]["max_train_samples"]
    max_validation_samples = config["training"]["max_validation_samples"]
    data_config = config["data"]
    
    training_dataset = load_dataset_file(
        data_config["train_path"], max_train_samples
    )
    validation_dataset = load_dataset_file(
        data_config["validation_path"], max_validation_samples
    )

    return training_dataset, validation_dataset

def configure_qlora(config):
    quantization = config["quantization"]
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=quantization["load_in_4bit"],
        bnb_4bit_quant_type=quantization["quant_type"],
        bnb_4bit_use_double_quant=quantization["double_quant"],
        bnb_4bit_compute_dtype=DTYPE_MAP[quantization["compute_dtype"]],
    )

    lora = config["lora"]
    lora_config = LoraConfig(
        r=lora["rank"],
        lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"],
        target_modules=lora["target_modules"],
        bias=lora["bias"],
        task_type=lora["task_type"]
    )

    return quantization_config, lora_config

def apply_qlora_config(model, lora_config, gradient_checkpointing):
    model = prepare_model_for_kbit_training(
        model, use_gradient_checkpointing=gradient_checkpointing
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    model.config.use_cache = False

    return model

def build_model_config(config, quantization_config):
    model = config["model"]
    return {
        "pretrained_model_name_or_path": model["name"],
        "quantization_config": quantization_config,
        "device_map": "auto",
        "dtype": DTYPE_MAP[model["dtype"]],
    }

def load_model_and_tokenizer(model_config):
    model = AutoModelForCausalLM.from_pretrained(**model_config)
    tokenizer = AutoTokenizer.from_pretrained(
        model_config["pretrained_model_name_or_path"]
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return model, tokenizer

def format_training_example(sample):
    passage = sample["Meta(Refine)"]["passage"]
    summary = sample["Annotation"]["summary3"]

    return {
        "prompt": [
            {
                "role": "user",
                "content": (
                    "다음 원문의 핵심 내용을 한국어로 간결하게 요약하세요. "
                    "원문에 없는 사실은 추가하지 마세요.\n\n"
                    f"### 원문 텍스트:\n{passage}"
                ),
            }
        ],
        "completion": [
            {
                "role": "assistant",
                "content": summary,
            }
        ],
    }

def prepare_training_dataset(dataset):
    return dataset.map(
        format_training_example,
        batched=False,
        remove_columns=dataset.column_names,
    )

def configure_training(config):
    training_config = config["training"]
    evaluation_config = config["evaluation"]
    checkpoint_config = config["checkpoint"]

    return SFTConfig(
        num_train_epochs=training_config["epochs"],
        per_device_train_batch_size=training_config["batch_size"],
        learning_rate=training_config["learning_rate"],
        gradient_accumulation_steps=training_config["gradient_accumulation_steps"],
        logging_steps=training_config["logging_steps"],
        optim=training_config["optim"],
        gradient_checkpointing=training_config["gradient_checkpointing"],
        dataloader_pin_memory=training_config["dataloader_pin_memory"],
        report_to=training_config["report_to"],

        eval_strategy=evaluation_config["strategy"],
        eval_steps=evaluation_config["eval_steps"],
        load_best_model_at_end=evaluation_config["load_best_model_at_end"],
        metric_for_best_model=evaluation_config["metric_for_best_model"],
        greater_is_better=evaluation_config["greater_is_better"],

        output_dir=str(BASE_DIR / checkpoint_config["output_dir"]),
        save_strategy=checkpoint_config["save_strategy"],
        save_steps=checkpoint_config["save_steps"],
        save_total_limit=checkpoint_config["save_total_limit"],

        max_length=config["model"]["max_sequence_length"],
        completion_only_loss=True,
    )

def apply_training_config(
    model, tokenizer, training_dataset, validation_dataset, training_args
):
    return SFTTrainer(
        model=model,
        args=training_args,
        processing_class=tokenizer,
        train_dataset=training_dataset,
        eval_dataset=validation_dataset,
    )

def train(trainer, config):
    resume_from_checkpoint = config["training"]["resume_from_checkpoint"]
    if isinstance(resume_from_checkpoint, str):
        resume_from_checkpoint = str(BASE_DIR / resume_from_checkpoint)

    trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    print(f"    Best checkpoint: {trainer.state.best_model_checkpoint}")

if __name__ == "__main__":
    print("1. Loading config...")
    config = load_config()

    print("2. Loading datasets...")
    training_dataset, validation_dataset = load_datasets(config)
    
    print("3. Formatting datasets...")
    training_dataset = prepare_training_dataset(training_dataset)
    validation_dataset = prepare_training_dataset(validation_dataset)
    
    print("4. Configuring QLoRA...")
    quantization_config, lora_config = configure_qlora(config)
    
    print("5. Configuring model...")
    model_config = build_model_config(config, quantization_config)
    
    print("6. Configuring training...")
    training_args = configure_training(config)
    
    print("7. Loading model and tokenizer...")
    model, tokenizer = load_model_and_tokenizer(model_config)
    
    print("8. Applying QLoRA config...")
    model = apply_qlora_config(model, lora_config, training_args.gradient_checkpointing)
    
    print("9. Creating trainer and tokenizing datasets...")
    trainer = apply_training_config(
        model, tokenizer, training_dataset, validation_dataset, training_args
    )
    
    print("10. Starting training...")
    train(trainer, config)
    
    print("11. Finished!")
