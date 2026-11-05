# Task 03 · KFP v2 Pipeline·실험 비교

Pipeline ServiceAccount, S3 Secret skeleton, compiled definition/evidence ConfigMap이 제공된다.

`ai267 start 03`은 `ex267-t03-pipeline/exam-provided-minio`에 endpoint, 전용 bucket과 자격 증명을 시험 제공값으로 준비한다. OpenShift Console의 **Workloads → Secrets → exam-provided-minio**에서 값을 확인해 채점 대상 `aws-connection-fraud-s3`와 DSPA 설정에 적용한다. 대상 Secret과 starter YAML은 계속 미완성 상태로 제공된다.

시작 시 합성 데이터가 `s3://ex267-task03/data/transactions.csv`에 업로드되고 `dspa-db` Secret, `exam-provided-pipeline-source/fraud_pipeline.py`가 준비된다. 소스는 공개 AI26X의 pipeline artifact/experiment 패턴을 RHOAI 3.3과 문제의 `max_depth` 비교에 맞게 조정한 입력 자료다. 컴파일·업로드·두 run 실행·승인 판단은 응시자가 수행한다.

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

