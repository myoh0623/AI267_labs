# Task 03 · KFP v2 Pipeline·실험 비교

Pipeline ServiceAccount, S3 Secret skeleton, compiled definition/evidence ConfigMap이 제공된다.

## 수행 목표

1. 실제 S3 값을 설정하고 `resources/dspa-starter.yaml`로 DSPA를 Ready로 만든다.
2. Python 3.11+와 KFP 2.14.3+로 `validate`, `train`, `evaluate` 컴포넌트를 컴파일한다.
3. compiled YAML을 `fraud-training-pipeline` ConfigMap에 저장하고 `ex267.io/kfp-sdk` annotation을 기록한다.
4. ServiceAccount, Secret, requests/limits, cache/retry/run prefix 증적을 `pipeline-evidence`에 기록한다.
5. 서로 다른 `max_depth` 두 run을 성공시키고 생성 Workflow에 `ex267.io/max-depth` label을 붙인다.
6. 승인 model URI와 SHA-256을 기록한다.

```bash
../../exam-lab.sh grade 03
```

