from peft import PeftModel
import torch
from pathlib import Path
import yaml
import json
import time
from tqdm import tqdm
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig
)

DTYPE_MAP = {
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
    "float32": torch.float32,
}

BASE_DIR = Path(__file__).resolve().parent

class StepTimer:
    def __init__(self):
        self.last_time = time.time()

    def print_step(self, current_step, total_steps):
        now = time.time()
        elapsed = now - self.last_time
        self.last_time = now

        progress = (current_step / total_steps) * 100

        print(
            f"Step {current_step}/{total_steps} "
            f"({progress:.1f}%) - {elapsed:.2f}s"
        )

def load_config():
    with (BASE_DIR / "config.yaml").open(encoding="utf-8") as file:
        return yaml.safe_load(file)

def load_golden_dataset(config, sample_limit=100):
    data_path = BASE_DIR / config["dataset"]["golden_path"]
    with data_path.open(encoding="utf-8") as file:
        data = json.load(file)
    if sample_limit is not None:
        data = data[:sample_limit]

    return Dataset.from_list(data)

def build_quant_config(config):
    quantization = config["quantization"]
    return BitsAndBytesConfig(
        load_in_4bit=quantization["load_in_4bit"],
        bnb_4bit_quant_type=quantization["quant_type"],
        bnb_4bit_use_double_quant=quantization["double_quant"],
        bnb_4bit_compute_dtype=DTYPE_MAP[quantization["compute_dtype"]],
    )

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

def load_adapter(model, config):
    adapter_path = BASE_DIR / config["checkpoint"]["output_dir"]
    return PeftModel.from_pretrained(
        model,
        adapter_path
    )

def build_messages(passage):
    return [
        {
            "role": "user",
            "content": (
                "다음 원문의 핵심 내용을 한국어로 간결하게 요약하세요. "
                "원문에 없는 사실은 추가하지 마세요. "
                "생각 과정은 출력하지 말고 요약문만 작성하세요.\n\n"
                f"### 원문 텍스트:\n{passage}"
            ),
        }
    ]

def tokenize_prompt(model, tokenizer, messages):
    # messages를 Qwen의 채팅 프롬프트 형식으로 변환
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    # prompt 텍스트 -> 토큰
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=tokenizer.model_max_length,
    ).to(model.device)
    return inputs

def generate_output(model, tokenized_prompt):
    # 모델에게 토큰 전달 -> 결과 출력
    with torch.no_grad():
        outputs = model.generate(
            **tokenized_prompt,
            max_new_tokens=256,
        )
    return outputs[0][tokenized_prompt["input_ids"].shape[-1]:]

def decode_output(tokenizer, generated_tokens):
    return tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    ).strip()

def evaluate_single(model, tokenizer, golden_dataset):
    model.eval()
    sample = golden_dataset[2]
    result = evaluate_sample(model, tokenizer, sample)
    print("=== 생성 결과 ===")
    print(result["generated_summary"])
    print("\n=== 정답 결과 ===")
    print(result["expected_summary"])

def evaluate_sample(model, tokenizer, sample):
    passage = sample["Meta(Refine)"]["passage"]
    passage_id = sample["Meta(Refine)"]["passage_id"]
    expected_summary = sample["Annotation"]["summary3"]

    built_messages = build_messages(passage)
    tokenized_prompt = tokenize_prompt(model, tokenizer, built_messages)
    generated_tokens = generate_output(model, tokenized_prompt)
    generated_summary = decode_output(tokenizer, generated_tokens)
    return {
        "passage_id": passage_id,
        "expected_summary": expected_summary,
        "generated_summary": generated_summary,
    }

def evaluate_dataset(model, tokenizer, golden_dataset):
    model.eval()
    results = []
    timer = StepTimer()
    total_steps = len(golden_dataset)
    for current_step, sample in enumerate(
        tqdm(golden_dataset, desc="Evaluating"),
        start=1,
    ):        
        result = evaluate_sample(
            model,
            tokenizer,
            sample,
        )
        results.append(result)
    return results

def save_results(results, config):
    result_path = BASE_DIR / config["final_evaluation"]["result_path"]
    with result_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    config = load_config()
    golden_dataset = load_golden_dataset(config)
    quantization_config = build_quant_config(config)
    model_config = build_model_config(config, quantization_config)
    model, tokenizer = load_model_and_tokenizer(model_config)
    model = load_adapter(model, config)
    # evaluate(model, tokenizer, golden_dataset)
    evaluation_results = evaluate_dataset(model, tokenizer, golden_dataset)
    save_results(evaluation_results, config)