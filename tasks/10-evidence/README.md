# Task 10 · 재현·증적·롤백

통합 evidence와 rollback ConfigMap skeleton이 제공된다.

시작 시 합성 current/previous model, sample, environment lock과 clean replay Python 코드가 `exam-provided-replay-inputs`와 `s3://ex267-task10/replay/`에 준비된다. 고정 image 값도 입력으로 제공되지만 Job의 volume, command, 계보 manifest와 rollback 증적은 응시자가 완성한다.

## 수행 목표

1. clean Git SHA, environment/pipeline digest, secret scan 결과를 기록한다.
2. 모델을 export하고 깨끗한 프로세스에서 load/sample inference를 검증한다.
3. image/data/run/model/index/metric/approval/deployment/monitoring을 하나의 manifest로 연결한다.
4. `resources/clean-replay-starter.yaml`을 고정 image digest와 재현 명령으로 완성해 Job을 성공시킨다.
5. 이전 model/runtime digest로 rollback하고 endpoint/protocol을 재검증한다.

```bash
../../exam-lab.sh grade 10
```

