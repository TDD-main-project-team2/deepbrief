import argparse
from pathlib import Path

import torch
import yaml

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)
from peft import (
    LoraConfig,
    prepare_model_for_kbit_training,
    get_peft_model,
)
from trl import SFTTrainer, SFTConfig


# ============================================================
# Config
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()

MODEL_CONFIG = config["model"]
DATASET_CONFIG = config["dataset"]
QUANT_CONFIG = config["quantization"]
LORA_CONFIG = config["lora"]
TRAINING_CONFIG = config["training"]
CHECKPOINT_CONFIG = config["checkpoint"]
EVALUATION_CONFIG = config["evaluation"]
OUTPUT_CONFIG = config["output"]


# ============================================================
# Arguments
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--sample",
    type=int,
    default=None,
    help="학습/검증 데이터에서 사용할 샘플 수",
)

args = parser.parse_args()


# ============================================================
# Paths
# ============================================================

def resolve_path(path):
    path = Path(path)

    if path.is_absolute():
        return path

    return BASE_DIR / path


TRAIN_PATH = resolve_path(DATASET_CONFIG["train_path"])
VALIDATION_PATH = resolve_path(DATASET_CONFIG["validation_path"])

CHECKPOINT_DIR = resolve_path(
    CHECKPOINT_CONFIG["output_dir"]
)

BEST_ADAPTER_DIR = resolve_path(
    OUTPUT_CONFIG["best_adapter_dir"]
)


# ============================================================
# Model Settings
# ============================================================

MODEL_ID = MODEL_CONFIG["name"]

DTYPE_MAP = {
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
    "float32": torch.float32,
}

MODEL_DTYPE = DTYPE_MAP.get(
    MODEL_CONFIG["dtype"],
    torch.float16,
)


# ============================================================
# Load Tokenizer
# ============================================================

print("===== Loading Tokenizer =====")
print(f"Model: {MODEL_ID}")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


# ============================================================
# Load Dataset
# ============================================================

print("===== Loading Dataset =====")

dataset = load_dataset(
    "json",
    data_files={
        "train": str(TRAIN_PATH),
        "validation": str(VALIDATION_PATH),
    },
)

if args.sample is not None:
    sample_size = min(
        args.sample,
        len(dataset["train"]),
        len(dataset["validation"]),
    )

    dataset["train"] = dataset["train"].select(
        range(sample_size)
    )

    dataset["validation"] = dataset["validation"].select(
        range(sample_size)
    )

print(f"학습 데이터: {len(dataset['train'])}개")
print(f"검증 데이터: {len(dataset['validation'])}개")


# ============================================================
# Dataset -> Prompt / Completion
# ============================================================

def convert_to_prompt_completion(example):
    return {
        "prompt": [
            {
                "role": "user",
                "content": (
                    "주어진 뉴스 본문을 읽고 질문에 답하세요. "
                    "정답만 간결하게 답하세요. /no_think\n\n"
                    f"뉴스 본문:\n{example['context']}\n\n"
                    f"질문:\n{example['question']}"
                ),
            }
        ],
        "completion": [
            {
                "role": "assistant",
                "content": example["answer"],
            }
        ],
    }


dataset = dataset.map(
    convert_to_prompt_completion,
    remove_columns=dataset["train"].column_names,
)


# ============================================================
# 4-bit Quantization
# ============================================================

print("===== Configuring 4-bit Quantization =====")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=QUANT_CONFIG["load_in_4bit"],
    bnb_4bit_quant_type=QUANT_CONFIG["quant_type"],
    bnb_4bit_compute_dtype=DTYPE_MAP[
        QUANT_CONFIG["compute_dtype"]
    ],
    bnb_4bit_use_double_quant=QUANT_CONFIG["double_quant"],
)


# ============================================================
# Load Model
# ============================================================

print(f"===== Loading {MODEL_ID} =====")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    dtype=MODEL_DTYPE,
    device_map="auto",
    use_safetensors=True,
)

model = prepare_model_for_kbit_training(model)

model.config.use_cache = False


# ============================================================
# LoRA
# ============================================================

print("===== Configuring LoRA =====")

peft_config = LoraConfig(
    r=LORA_CONFIG["rank"],
    lora_alpha=LORA_CONFIG["alpha"],
    target_modules=LORA_CONFIG["target_modules"],
    lora_dropout=LORA_CONFIG["dropout"],
    bias=LORA_CONFIG["bias"],
    task_type=LORA_CONFIG["task_type"],
)

model = get_peft_model(
    model,
    peft_config,
)


# Trainable parameters -> FP16
for name, param in model.named_parameters():
    if param.requires_grad:
        param.data = param.data.to(torch.float16)


model.print_trainable_parameters()


# ============================================================
# Training Config
# ============================================================

print("===== Configuring Training =====")

training_args = SFTConfig(
    output_dir=str(CHECKPOINT_DIR),

    max_length=MODEL_CONFIG["max_sequence_length"],

    num_train_epochs=TRAINING_CONFIG["epochs"],

    per_device_train_batch_size=TRAINING_CONFIG[
        "batch_size"
    ],

    gradient_accumulation_steps=TRAINING_CONFIG[
        "gradient_accumulation_steps"
    ],

    learning_rate=TRAINING_CONFIG["learning_rate"],

    fp16=TRAINING_CONFIG["fp16"],
    bf16=TRAINING_CONFIG["bf16"],

    max_grad_norm=TRAINING_CONFIG["max_grad_norm"],

    logging_steps=TRAINING_CONFIG["logging_steps"],

    eval_strategy=EVALUATION_CONFIG["strategy"],
    eval_steps=EVALUATION_CONFIG["eval_steps"],

    save_strategy=CHECKPOINT_CONFIG["save_strategy"],
    save_steps=CHECKPOINT_CONFIG["save_steps"],
    save_total_limit=CHECKPOINT_CONFIG["save_total_limit"],

    load_best_model_at_end=EVALUATION_CONFIG[
        "load_best_model_at_end"
    ],

    metric_for_best_model=EVALUATION_CONFIG[
        "metric_for_best_model"
    ],

    greater_is_better=EVALUATION_CONFIG[
        "greater_is_better"
    ],

    gradient_checkpointing=TRAINING_CONFIG[
        "gradient_checkpointing"
    ],

    optim=TRAINING_CONFIG["optim"],

    report_to=TRAINING_CONFIG["report_to"],

    completion_only_loss=TRAINING_CONFIG[
        "completion_only_loss"
    ],

    dataloader_pin_memory=TRAINING_CONFIG[
        "dataloader_pin_memory"
    ],

    disable_tqdm=TRAINING_CONFIG[
        "disable_tqdm"
    ],
)


# ============================================================
# Trainer
# ============================================================

print("===== Creating Trainer =====")

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    processing_class=tokenizer,
)


# ============================================================
# Training
# ============================================================

print()
print("==============================================")
print(f"       {MODEL_ID} QLoRA Training Start")
print("==============================================")
print()

resume_checkpoint = TRAINING_CONFIG["resume_from_checkpoint"]

if resume_checkpoint:
    trainer.train(
        resume_from_checkpoint=resume_checkpoint
    )
else:
    trainer.train()


# ============================================================
# Training Finished
# ============================================================

print()
print("==============================================")
print("            Training Finished")
print("==============================================")
print()

print(
    f"Best checkpoint : "
    f"{trainer.state.best_model_checkpoint}"
)

print(
    f"Best eval loss  : "
    f"{trainer.state.best_metric}"
)


# ============================================================
# Save Best Adapter
# ============================================================

print()
print("===== Saving Best Adapter =====")

BEST_ADAPTER_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

trainer.save_model(
    str(BEST_ADAPTER_DIR)
)

print(
    f"Best Adapter saved to: "
    f"{BEST_ADAPTER_DIR}"
)