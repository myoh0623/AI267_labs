# Task 06 · Model Registry·계보

Model Registry는 클러스터 밖의 metadata API를 포함하므로 결과 ID와 digest를 `registry-evidence`에 저장한다.

## 수행 목표

1. `fraud-risk` 아래 1.0.0과 1.1.0을 서로 다른 version ID로 등록한다.
2. 각 version을 서로 다른 OCI digest에 연결하고 별도 pull/checksum을 수행한다.
3. source/data/run/format/metric/intended use/limitation/owner/approval metadata를 완성한다.
4. v1beta1 API 응답을 파일로 저장하고 SHA-256을 기록한다.
5. 1.1.0 exact digest를 배포하고 `deployment_artifact_digest`와 동일함을 기록한다.

Secret, token, API 응답 본문은 ConfigMap에 넣지 않는다.

```bash
../../exam-lab.sh grade 06
```

