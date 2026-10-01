import yaml
import torch
import time
from pathlib import Path
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainerCallback
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from trl import SFTTrainer, SFTConfig

class StepTimerCallback(TrainerCallback):
    def __init__(self):
        self.last_time = time.time()

    def on_step_end(self, args, state, control, **kwargs):
        now = time.time()
        elapsed = now - self.last_time

        total_steps = state.max_steps
        current_step = state.global_step
        progress = (current_step / total_steps) * 100

        print(
            f"Step {current_step}/{total_steps} "
            f"({progress:.1f}%) - {elapsed:.2f}s"
        )

        self.last_time = now

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
    def format_example(sample):
        passage = sample["Meta(Refine)"]["passage"]
        summary = sample["Annotation"]["summary3"]
        return {
            "prompt": [
                {
                    "role": "user",
                    "content": (
                        "다음 기사를 요약해주세요. 원문 없는 사실은 추가하지 마세요.\n\n"
                        f"### 원문 텍스트: \n{passage}"
                    )
                }
            ],
            "completion": [
                {
                    "role": "assistant",
                    "content": summary
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
        bias=config["lora"]["bias"],
        task_type=config["lora"]["task_type"],
        target_modules=config["lora"]["target_modules"]
    )
    return bnb_config, lora_config

def load_model(config, bnb_config):
    model_name = config["model"]["name"]
    dtype = getattr(torch, config["model"]["dtype"])

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        dtype=dtype
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
        num_train_epochs=config["training"]["epochs"],
        per_device_train_batch_size=config["training"]["batch_size"],
        learning_rate=config["training"]["learning_rate"],
        gradient_accumulation_steps=config["training"]["gradient_accumulation_steps"],
        bf16=config["training"]["bf16"],
        fp16=config["training"]["fp16"],
        logging_steps=config["training"]["logging_steps"],
        optim=config["training"]["optim"],
        gradient_checkpointing=config["training"]["gradient_checkpointing"],
        report_to=config["training"]["report_to"],

        eval_strategy=config["evaluation"]["strategy"],
        eval_steps=config["evaluation"]["eval_steps"],
        load_best_model_at_end=config["evaluation"]["load_best_model_at_end"],
        metric_for_best_model=config["evaluation"]["metric_for_best_model"],
        greater_is_better=config["evaluation"]["greater_is_better"],

        output_dir=str(Path(__file__).parent / config["checkpoint"]["output_dir"]),
        save_strategy=config["checkpoint"]["save_strategy"],
        save_steps=config["checkpoint"]["save_steps"],
        save_total_limit=config["checkpoint"]["save_total_limit"],

        max_length=config["model"]["max_seq_length"],
        completion_only_loss=True
    )
    return training_config, train_dataset, validation_dataset

def train(model, tokenizer, train_dataset, validation_dataset, lora_config, training_config, config):
    print("Preparing model for QLoRA...")
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)

    print("Trainable parameters:")
    model.print_trainable_parameters()

    print("Starting training...")
    trainer = SFTTrainer(
        model=model,
        args=training_config,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        processing_class=tokenizer,
        callbacks=[StepTimerCallback()]
    )
    trainer.train(resume_from_checkpoint=config["training"]["resume_from_checkpoint"])
    print(f"Best checkpoint: {trainer.state.best_model_checkpoint}")
    print("Training complete!")

if __name__ == "__main__":
    print("1. Loading config...")
    config = load_config()
    print("2. Loading dataset...")
    dataset = load_training_data(config)
    print("3. Formatting dataset...")
    dataset = format_dataset(dataset)
    print("4. Configuring QLoRA...")
    bnb_config, lora_config = configure_qlora(config)
    print("5. Loading model...")
    model, tokenizer = load_model(config, bnb_config)
    print("6. Configuring training...")
    training_config, train_dataset, validation_dataset = configure_training(
        config, dataset
    )
    print("7. Starting train()...")
    train(
        model,
        tokenizer,
        train_dataset,
        validation_dataset,
        lora_config,
        training_config,
        config
    )
    print("8. Finished!")