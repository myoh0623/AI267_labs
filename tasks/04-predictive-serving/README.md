# Task 04 · OpenVINO KServe 모델 서빙

모델 계약과 S3 Secret skeleton만 제공된다. `fraud-v2` InferenceService는 응시자가 만든다.

## 수행 목표

1. `models/fraud/2/`의 ONNX checksum을 확인하고 S3 connection을 완성한다.
2. 설치 환경의 OpenVINO ServingRuntime 이름을 찾아 `resources/inferenceservice-starter.yaml`을 수정한다.
3. CPU request/limit 1, memory request/limit 2Gi를 적용한다.
4. Ready condition과 URL을 확인한다.
5. 정상 V2 요청과 invalid shape 요청의 HTTP/response digest를 `serving-evidence`에 기록한다.
6. 재생성 및 이전 승인 모델 rollback을 수행하고 증적을 갱신한다.

```bash
../../exam-lab.sh grade 04
```

