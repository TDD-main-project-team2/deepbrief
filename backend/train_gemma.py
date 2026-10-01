import argparse
import torch

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import (
    LoraConfig,
    prepare_model_for_kbit_training,
)
from trl import SFTTrainer


MODEL_ID = "google/gemma-2-2b-it"

TRAIN_PATH = "./fine_tuning/qa/data/processed/training_dataset.json"
VALIDATION_PATH = "./fine_tuning/qa/data/processed/validation_dataset.json"

CHECKPOINT_DIR = "./fine_tuning/qa/checkpoints"
BEST_ADAPTER_DIR = "./fine_tuning/qa/adapters/best"

parser = argparse.ArgumentParser()
parser.add_argument("--sample", type=int, default=None)
args = parser.parse_args()


# -----------------------------
# 1. Tokenizer
# -----------------------------
print("===== Loading Tokenizer =====")

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


# -----------------------------
# 2. Dataset
# -----------------------------
dataset = load_dataset(
    "json",
    data_files={
        "train": TRAIN_PATH,
        "validation": VALIDATION_PATH,
    },
)

# --sample 3 처리
if args.sample:
    dataset["train"] = dataset["train"].select(
        range(min(args.sample, len(dataset["train"])))
    )
    dataset["validation"] = dataset["validation"].select(
        range(min(args.sample, len(dataset["validation"])))
    )

print(f"학습 데이터: {len(dataset['train'])}개")
print(f"검증 데이터: {len(dataset['validation'])}개")

# ============================================================
# 3. Formatting
# ============================================================

def format_example(example):
    messages = [
        {
            "role": "user",
            "content": (
                "주어진 뉴스 본문을 읽고 질문에 답하세요.\n\n"
                f"뉴스 본문:\n{example['context']}\n\n"
                f"질문:\n{example['question']}"
            ),
        },
        {
            "role": "assistant",
            "content": example["answer"],
        },
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )


# -----------------------------
# 4. 4-bit Quantization
# -----------------------------
print("===== Configuring 4-bit Quantization =====")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)


# -----------------------------
# 5. Model
# -----------------------------
print("===== Loading Gemma 2 2B IT =====")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    use_safetensors=True,
)

model = prepare_model_for_kbit_training(model)

model.config.use_cache = False


# -----------------------------
# 6. LoRA
# -----------------------------
print("===== Configuring LoRA =====")

peft_config = LoraConfig(
    r=8,
    lora_alpha=16,

    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)


# -----------------------------
# 7. Training Arguments
# -----------------------------
print("===== Configuring Training =====")

training_args = TrainingArguments(
    output_dir=CHECKPOINT_DIR,

    num_train_epochs=1,

    # GPU 실제 배치
    per_device_train_batch_size=1,

    # 유효 batch size = 1 × 16 = 16
    gradient_accumulation_steps=1,

    learning_rate=2e-4,

    fp16=False,
    bf16=False,

    logging_steps=10,

    # 250 step마다 평가
    eval_strategy="steps",
    eval_steps=1,

    # 250 step마다 checkpoint
    save_strategy="steps",
    save_steps=1,

    # Best checkpoint 자동 선택
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,

    # Memory optimization
    gradient_checkpointing=True,

     # 8-bit optimizer
    optim="paged_adamw_8bit",

    # Logging
    report_to="none",

)


# -----------------------------
# 8. Trainer
# -----------------------------
print("===== Creating Trainer =====")

trainer = SFTTrainer(
    model=model,
    args=training_args,

    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],

    processing_class=tokenizer,

    peft_config=peft_config,

    formatting_func=format_example,
)


# ============================================================
# 9. Train
# ============================================================

print()
print("==============================================")
print("      Gemma 2 2B IT QLoRA Training Start")
print("==============================================")
print()

trainer.train()


# ============================================================
# 10. Training Result
# ============================================================

print()
print("==============================================")
print("           Training Finished")
print("==============================================")
print()

print(f"Best checkpoint : {trainer.state.best_model_checkpoint}")
print(f"Best eval loss  : {trainer.state.best_metric}")


# ============================================================
# 11. Save Best Adapter
# ============================================================

print()
print("===== Saving Best Adapter =====")

trainer.save_model(BEST_ADAPTER_DIR)

print(f"Best Adapter saved to: {BEST_ADAPTER_DIR}")