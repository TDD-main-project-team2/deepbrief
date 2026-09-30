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
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)

# 실행 위치에 관계없이 스크립트 옆의 YAML 설정을 읽는다.
config_path = Path(__file__).resolve().parent / "config.yaml"
with config_path.open(encoding="utf-8") as file:
    config = yaml.safe_load(file)

dtype_map = {
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
    "float32": torch.float32,
}
sample_limit = config["data"]["sample_limit"]
if sample_limit is not None and (type(sample_limit) is not int or sample_limit < 1):
    raise ValueError("data.sample_limit은 양의 정수 또는 null이어야 합니다.")
training_config = config["training"]

# 사용할 학습 장치 선택
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"사용 장치: {device}")

data_path = config_path.parent / config["data"]["train_path"]
with data_path.open(encoding="utf-8") as file:
    data = json.load(file)
if sample_limit is not None:
    data = data[:sample_limit]

dataset = Dataset.from_list(data)

output_dir = config_path.parent / training_config["output_dir"]

# 4비트 양자화 설정
quantization_config = BitsAndBytesConfig(
    load_in_4bit=config["quantization"]["load_in_4bit"],
    bnb_4bit_quant_type=config["quantization"]["quant_type"],
    bnb_4bit_use_double_quant=config["quantization"]["double_quant"],
    bnb_4bit_compute_dtype=dtype_map[config["quantization"]["compute_dtype"]],
)

# 설정대로 모델 불러오기
model_name = config["model"]["name"]
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=quantization_config,
    device_map="auto",
    dtype=dtype_map[config["model"]["dtype"]],
)
model = prepare_model_for_kbit_training(
    model, use_gradient_checkpointing=training_config["gradient_checkpointing"]
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

lora_config = LoraConfig(
    r=config["lora"]["rank"],
    lora_alpha=config["lora"]["alpha"],
    target_modules=config["lora"]["target_modules"],
    lora_dropout=config["lora"]["dropout"],
    bias=config["lora"]["bias"],
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
model.config.use_cache = False  # KV 캐시: 학습 중에는 off, 추론 시에는 on


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


MAX_SEQUENCE_LENGTH = config["data"]["max_sequence_length"]


def tokenize(example):
    """원문과 요약을 토큰화하고, 정답 요약만 학습하도록 labels를 만든다."""

    messages = build_training_messages(example)

    prompt_ids = tokenizer.apply_chat_template(
        messages[:-1],
        tokenize=True,
        add_generation_prompt=True,
        return_dict=False,
    )

    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
        return_dict=False,
    )

    prompt_length = len(prompt_ids)
    sequence_length = len(input_ids)

    if input_ids[:prompt_length] != prompt_ids:
        raise ValueError("대화 템플릿의 입력/정답 경계가 일치하지 않습니다.")

    if sequence_length > MAX_SEQUENCE_LENGTH:
        passage_id = example["Meta(Refine)"].get("passage_id", "알 수 없음")
        raise ValueError(
            f"{passage_id}: {sequence_length}토큰으로 {MAX_SEQUENCE_LENGTH}을 초과합니다."
        )

    if sequence_length <= prompt_length:
        raise ValueError("학습할 정답 토큰이 없습니다.")

    return {
        "input_ids": input_ids,
        "attention_mask": [1] * sequence_length,
        "labels": [-100] * prompt_length + input_ids[prompt_length:],
    }


tokenized_dataset = dataset.map(
    tokenize, batched=False, remove_columns=dataset.column_names
)

args = TrainingArguments(
    output_dir=str(output_dir),
    per_device_train_batch_size=training_config["batch_size"],
    gradient_accumulation_steps=training_config["gradient_accumulation_steps"],
    learning_rate=training_config["learning_rate"],
    num_train_epochs=training_config["epochs"],
    max_steps=training_config["max_steps"],
    logging_steps=training_config["logging_steps"],
    save_strategy=training_config["save_strategy"],
    save_total_limit=training_config["save_total_limit"],
    optim=training_config["optim"],
    gradient_checkpointing=training_config["gradient_checkpointing"],
    dataloader_pin_memory=training_config["dataloader_pin_memory"],
    report_to=training_config["report_to"],
)

trainer = Trainer(
    model=model,
    train_dataset=tokenized_dataset,
    args=args,
    data_collator=DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        padding=True,
        label_pad_token_id=-100,
    ),
)

trainer.train()

trainer.save_model(str(output_dir / "final-adapter"))  # 어댑터 저장
tokenizer.save_pretrained(str(output_dir / "final-adapter"))  # 토크나이저 저장
print(f"어댑터 저장 완료: {output_dir / 'final-adapter'}")

model.eval()  # 평가·추론 모드로 전환
model.config.use_cache = True

# 테스트할 원문(학습 후 추론에만 사용)
test_passage = """
소방청(청장 정문호)은 국내 거주 외국인의 수가 증가함에 따라 외국인을 대상으로 안전에 대한 관심을 유발하고 맞춤 정책을 발굴하기 위해 유튜브 영상을 제작한다고 밝혔다.
국내에 거주하는 외국인은 귀화, 결혼이민, 구직, 유학 등의 형태로 다양화되고 있고, 최근 3년간 지속적으로 증가하여 지난 해 250만명을 넘어섰다.
그동안 소방청은 외국인을 대상으로 한 다중언어 홍보자료 배포나 학생들 대상의 방문 교육 등을 실시해왔다.
그리고 이번에는 국내에 거주하는 외국인의 객관적인 시각과 경험을 통해서 한국 소방서비스의 장단점을 들어보고자 유튜브 영상을 만들게 되었다고 밝혔다.
외국인 대상 첫 영상인 ‘어서 와, 한국안전은 처음이지(easy)’는 한국에 6년째 거주하는 오스트리아 출신 모델 겸 배우 케이디(Kady) 가 출연해 한국 생활 중 겪은 화재와 교통사고 경험을 들려줄 계획이다.
케이디는 자신의 고향인 오스트리아, 학창 시절을 보냈던 미국, 중국 등 다양한 국가에서 생활하며 보고 느꼈던 나라별 소방서비스를 비교해 외국인 뿐 아니라 내국인도 흥미롭게 볼 수 있을 것으로 보인다.
조선호 소방청 대변인은 한국 문화가 세계적으로 인기가 올라가는 만큼 국내에 살거나 여행하는 외국인들에게 안전이 더욱 중요해지고 있다고 말하고 앞으로 이들과 편리하게 소통할 수 있는 교육홍보물을 늘려가겠다고 밝혔다.
""".strip()

if not test_passage:
    raise ValueError("요약할 원문을 입력하세요.")

inference_prompt = tokenizer.apply_chat_template(
    build_summary_messages(test_passage),
    tokenize=False,
    add_generation_prompt=True,
)
inputs = tokenizer(inference_prompt, add_special_tokens=False, return_tensors="pt").to(
    device
)

with torch.inference_mode():
    outputs = model.generate(
        **inputs,
        max_new_tokens=config["generation"]["max_new_tokens"],
        do_sample=config["generation"]["do_sample"],
        pad_token_id=tokenizer.pad_token_id,
    )

answer = outputs[0, inputs["input_ids"].shape[1] :]
print(tokenizer.decode(answer, skip_special_tokens=True))
