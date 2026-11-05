# Task 08 · LLM 최적화·LMEval

재현 가능한 작은 INT8 실습용 script/PVC와 Job·LMEval starter가 제공된다.

`synthetic-baseline`과 `synthetic-optimized`는 합성 응답을 반환하는 소형 OpenAI completions 호환 Service다. 연결값은 `exam-provided-evaluation-inputs`에 있다. 클러스터 Pod가 Hugging Face CDN을 해석하지 못하므로 시작 시 RHOAI LM-Eval 이미지와 동일한 버전으로 OpenBookQA/GPT-2 cache를 만들고 MinIO `lmeval/`에 제공한다. Starter는 `allowOnline: false`와 offline S3를 사용하며, CR 안에 외부 다운로드가 필요 없는 합성 한국어·안전 Unitxt `taskRecipes`도 포함한다. 실제 LLM 품질을 주장하는 환경이 아니며, CR 실행·결과 보존·비교 절차를 연습하기 위한 입력이다.

## 수행 목표

1. baseline model/runtime/hardware/precision/context/dataset/seed를 고정한다.
2. `resources/quantization-job-starter.yaml`을 적용해 `quantize-support-llm` Job을 성공시킨다.
3. optimized artifact SHA-256과 `Developer Preview` 지원 상태를 기록한다.
4. `resources/lmevaljob-starter.yaml`을 복제해 baseline/optimized LMEvalJob을 각각 실행한다.
5. standard·한국어·safety 결과와 실패 표본을 비교하고 승격/rollback 결정을 기록한다.

```bash
../../exam-lab.sh grade 08
```

