# SUMMARY 어댑터 폴더

서비스(`backend/services/ai/model_service.py`)가 요약 LoRA 어댑터를 불러오는 기본 위치입니다.

- 팀이 학습한 summary 어댑터의 `checkpoint-500` 폴더 **안의 파일**을 이 폴더에 넣으세요 (`adapter_config.json`, `adapter_model.safetensors` 등).
- 체크포인트 안의 `README.md`는 넣지 마세요. 이 안내 파일을 덮어씁니다.
- 어댑터는 팀 학습 결과라 레포에 올리지 않습니다. 커밋할 때 이 폴더에서 `README.md` 외 파일이 포함되지 않았는지 확인하세요.
- 다른 위치를 쓰려면 `.env`에 `SUMMARY_ADAPTER_PATH`를 지정하세요.
