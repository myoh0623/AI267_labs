# Task 06 · Model Registry·계보

Model Registry의 실제 metadata API 결과 ID와 digest를 `registry-evidence`에 저장한다. RHOAI 3.3의 Kubernetes ModelRegistry CR은 `modelregistry.opendatahub.io/v1beta1`이지만, 모델 데이터 REST API는 `/api/model_registry/v1alpha3`이다.

`ai267 start 06`은 교재의 `serving-modelregistry` Lab을 시작한다. 이 Lab이 RHOAI Model Registry component, MariaDB, `redhattraining-model-registry`, 교실 OCI registry와 ONNX v1/v2 파일을 준비한다. 위치는 `exam-provided-registry-inputs`에 기록되며, `fraud-risk` 등록과 두 버전의 build/push/배포는 응시자가 수행한다.

## 수행 목표

1. `fraud-risk` 아래 1.0.0과 1.1.0을 서로 다른 version ID로 등록한다.
2. 각 version을 서로 다른 OCI digest에 연결하고 별도 pull/checksum을 수행한다.
3. Registry의 model/version custom properties에 `git_revision`, `data_reference`, `pipeline_run`, `metrics`, `intended_use`, `limitations`, `owner`, `approval`을 같은 이름으로 기록하고 artifact의 `modelFormatName`을 `format`과 일치시킨다.
4. RHOAI 3.3 REST v1alpha3 API 응답을 파일로 저장하고 `registry_api_path=/api/model_registry/v1alpha3` 및 SHA-256을 기록한다.
5. 1.1.0 exact digest를 `ex267-t06-registry`에 배포한다. InferenceService를 Ready로 만들고 Registry에서 배포하면 추가되는 `modelregistry.opendatahub.io/registered-model-id`, `modelregistry.opendatahub.io/model-version-id`, `modelregistry.opendatahub.io/name` 라벨을 유지한다. `deployment_artifact_digest`는 1.1.0 digest와 같아야 한다.

외부 Route는 제공되지 않는다. `exam-provided-registry-inputs`의 `registry_service`, `registry_service_port`, `registry_rest_api`, `registry_proxy_prefix`를 사용해 API server의 Service proxy로 조회한다.

Secret, token, API 응답 본문은 ConfigMap에 넣지 않는다.

```bash
../../exam-lab.sh grade 06
```

