import yaml
import torch
from pathlib import Path
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from trl import SFTTrainer, SFTConfig

def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config

def load_training_data(config):
    base_dir = Path(__file__).parent
    dataset = load_dataset(
        "json",
        data_files={
            "train": str(base_dir / config["dataset"]["train_path"]),
            "validation": str(base_dir / config["dataset"]["validation_path"])
        }
    )
    return dataset

def format_dataset(dataset):
    def format_example(example):
        return {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "다음 기사를 요약해주세요.\n\n"
                        + example["Meta(Refine)"]["passage"]
                    )
                },
                {
                    "role": "assistant",
                    "content": example["Annotation"]["summary3"]
                }
            ]
        }
    return dataset.map(format_example)

def configure_qlora(config):
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=config["quantization"]["load_in_4bit"],
        bnb_4bit_quant_type=config["quantization"]["quant_type"],
        bnb_4bit_compute_dtype=getattr(
            torch,
            config["quantization"]["compute_dtype"]),
        bnb_4bit_use_double_quant=config["quantization"]["use_double_quant"]
    )

    lora_config = LoraConfig(
        r=config["lora"]["r"],
        lora_alpha=config["lora"]["alpha"],
        lora_dropout=config["lora"]["dropout"],
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear"
    )
    return bnb_config, lora_config

def load_model(config, bnb_config):
    model_name = config["model"]["name"]
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config
    )
    return model, tokenizer

def configure_training(config, dataset):
    max_train_samples = config["training"]["max_train_samples"]
    max_validation_samples = config["training"]["max_validation_samples"]

    train_dataset = dataset["train"].select(
        range(min(max_train_samples, len(dataset["train"])))
    )

    validation_dataset = dataset["validation"].select(
        range(min(max_validation_samples, len(dataset["validation"])))
    )

    training_config = SFTConfig(
        output_dir="checkpoints",
        num_train_epochs=config["training"]["epochs"],
        per_device_train_batch_size=config["training"]["batch_size"],
        learning_rate=config["training"]["learning_rate"],
        gradient_accumulation_steps=config["training"]["gradient_accumulation_steps"],
        eval_strategy="steps",
        eval_steps=config["evaluation"]["eval_steps"],
        save_strategy="steps",
        save_steps=config["checkpoint"]["save_steps"],
        save_total_limit=config["checkpoint"]["save_total_limit"],
        max_length=config["model"]["max_seq_length"],
        bf16=False,
        fp16=True,
        logging_steps=1,
        report_to="none"
    )
    return training_config, train_dataset, validation_dataset

def train(model, tokenizer, train_dataset, validation_dataset, lora_config, training_config):
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)

    trainer = SFTTrainer(
        model=model,
        args=training_config,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        processing_class=tokenizer
    )

    trainer.train()


if __name__ == "__main__":
    config = load_config()
    dataset = load_training_data(config)
    dataset = format_dataset(dataset)
    bnb_config, lora_config = configure_qlora(config)
    model, tokenizer = load_model(config, bnb_config)
    training_config, train_dataset, validation_dataset = configure_training(config, dataset)
    train(model, tokenizer, train_dataset, validation_dataset, lora_config, training_config)