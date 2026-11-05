# Task 08 · LLM 최적화·LMEval

재현 가능한 작은 INT8 실습용 script/PVC와 Job·LMEval starter가 제공된다.

## 수행 목표

1. baseline model/runtime/hardware/precision/context/dataset/seed를 고정한다.
2. `resources/quantization-job-starter.yaml`을 적용해 `quantize-support-llm` Job을 성공시킨다.
3. optimized artifact SHA-256과 `Developer Preview` 지원 상태를 기록한다.
4. `resources/lmevaljob-starter.yaml`을 복제해 baseline/optimized LMEvalJob을 각각 실행한다.
5. standard·한국어·safety 결과와 실패 표본을 비교하고 승격/rollback 결정을 기록한다.

```bash
../../exam-lab.sh grade 08
```

