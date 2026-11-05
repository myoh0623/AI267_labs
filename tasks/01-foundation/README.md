# Task 01 · 프로젝트·RBAC·S3 연결

초기 상태에는 팀/환경 라벨이 없고 `developer1`은 `view`만 가지며 `fraud-s3`는 구식 annotation과 placeholder 값을 사용한다.

`ai267 start 01`은 `ex267-fraud/exam-provided-minio`에 endpoint, 전용 bucket과 자격 증명을 시험 제공값으로 준비한다. OpenShift Console의 **Workloads → Secrets → exam-provided-minio**에서 값을 확인해 채점 대상 `fraud-s3`에 적용한다. `fraud-s3` 자체는 정답이 아니므로 `REPLACE_ME` 상태로 시작한다.

## 수행 목표

1. `ex267-fraud`에 `team=northstar-risk`, `environment=exam`을 설정한다.
2. `developer1`에게 namespace 범위 `edit`만 부여하고 `admin`/`cluster-admin`은 제거한다.
3. `fraud-s3`에 실제 endpoint/bucket/credential을 넣고 `opendatahub.io/connection-type-protocol=s3`를 설정한다.
4. `fraud-input-contract`의 CSV를 `input/transactions.csv`로 올린 뒤 고유 결과를 쓰고 새 프로세스에서 재조회한다.
5. `fraud-s3-evidence`의 다섯 key를 실제 object key와 SHA-256으로 갱신한다.

```bash
../../exam-lab.sh grade 01
```

채점기는 Secret 값 자체를 출력하지 않는다.

