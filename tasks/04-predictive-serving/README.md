# Task 04 · OpenVINO KServe 모델 서빙

모델 계약과 S3 Secret skeleton만 제공된다. `fraud-v2` InferenceService는 응시자가 만든다.

`ai267 start 04`는 `ex267-t04-serving/exam-provided-minio`에 endpoint, 전용 bucket과 자격 증명을 시험 제공값으로 준비한다. OpenShift Console의 **Workloads → Secrets → exam-provided-minio**에서 값을 확인해 채점 대상 `fraud-s3`와 모델 저장 경로에 적용한다. 대상 Secret과 InferenceService starter는 계속 미완성 상태로 제공된다.

교재의 diabetes ONNX v2와 v1은 각각 `models/fraud/2/`와 `models/fraud/1/`에 업로드된다. `exam-provided-model-artifacts`에 URI·SHA-256·입력 shape가 있고, 공식 `kserve-ovms` ServingRuntime도 namespace에 준비된다. InferenceService, data connection, 요청과 rollback은 자동 완성하지 않는다.

이 클러스터의 RHOAI 3.3.1 connection webhook은 `model.storage`는 주입하지만 KServe가 요구하는 `storage-config` bridge를 만들지 않는다. `start`가 같은 입력 자격 증명으로 이 기반 Secret만 보완한다. 채점 대상 `fraud-s3`, connection annotation, checksum과 서비스는 여전히 직접 완성한다.

## 수행 목표

1. `models/fraud/2/`의 ONNX checksum을 확인하고 S3 connection을 완성한다.
2. 설치 환경의 OpenVINO ServingRuntime 이름을 찾아 `resources/inferenceservice-starter.yaml`을 수정한다. Starter의 `opendatahub.io/connections`와 `opendatahub.io/connection-path`가 S3 Secret과 모델 경로를 연결하며, OpenShift AI가 `storageUri`를 주입한다.
3. CPU request/limit 1, memory request/limit 2Gi를 적용한다.
4. Ready condition과 URL을 확인한다.
5. 정상 V2 요청과 invalid shape 요청의 HTTP/response digest를 `serving-evidence`에 기록한다.
6. 재생성 및 이전 승인 모델 rollback을 수행하고 증적을 갱신한다.

```bash
../../exam-lab.sh grade 04
```

