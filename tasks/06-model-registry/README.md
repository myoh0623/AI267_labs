# Task 06 · Model Registry·계보

Model Registry의 실제 metadata API 결과 ID와 digest를 `registry-evidence`에 저장한다. RHOAI 3.3의 Kubernetes ModelRegistry CR은 `modelregistry.opendatahub.io/v1beta1`이지만, 모델 데이터 REST API는 `/api/model_registry/v1alpha3`이다.

`ai267 start 06`은 교재의 `serving-modelregistry` Lab을 시작한다. 이 Lab이 RHOAI Model Registry component, MariaDB, `redhattraining-model-registry`와 ONNX v1/v2 파일을 준비한다. 교실 공용 Registry는 push 자격 증명을 제공하지 않으므로 시험 namespace에는 임의 자격 증명과 PVC를 사용하는 전용 `practice-oci-registry`도 자동으로 준비한다. 위치는 `exam-provided-registry-inputs`, 로그인 값은 `exam-provided-oci-credentials`에 기록된다. 클러스터 pull용 `exam-provided-oci-pull`은 기본 ServiceAccount에 자동 연결되지만, `fraud-risk` 두 버전의 build/push/pull/등록/배포는 응시자가 수행한다.

## 수행 목표

1. `fraud-risk` 아래 1.0.0과 1.1.0을 서로 다른 version ID로 등록한다.
2. 각 version을 서로 다른 OCI digest에 연결하고 별도 pull/checksum을 수행한다.
3. Registry의 model/version custom properties에 `git_revision`, `data_reference`, `pipeline_run`, `metrics`, `intended_use`, `limitations`, `owner`, `approval`을 같은 이름으로 기록하고 artifact의 `modelFormatName`을 `format`과 일치시킨다.
4. RHOAI 3.3 REST v1alpha3 API 응답을 파일로 저장하고 `registry_api_path=/api/model_registry/v1alpha3` 및 SHA-256을 기록한다.
5. 1.1.0 exact digest를 `ex267-t06-registry`에 배포한다. InferenceService를 Ready로 만들고 Registry에서 배포하면 추가되는 `modelregistry.opendatahub.io/registered-model-id`, `modelregistry.opendatahub.io/model-version-id`, `modelregistry.opendatahub.io/name` 라벨을 유지한다. `deployment_artifact_digest`는 1.1.0 digest와 같아야 한다.

Model Registry REST의 외부 Route는 제공되지 않는다. `exam-provided-registry-inputs`의 `registry_service`, `registry_service_port`, `registry_rest_api`, `registry_proxy_prefix`를 사용해 API server의 Service proxy로 조회한다. 별도로 제공되는 `practice-oci-registry` Route는 모델 artifact push/pull 용도다.

OCI push/pull은 전용 Registry Route와 제공 credential을 사용한다. 자격 증명을 터미널에 출력하지 말고 `--password-stdin`으로 전달하며, 실습 인증서에서는 `--tls-verify=false`를 사용한다.
KServe ModelCar image는 `/models/model.onnx`와 modelcar lifecycle 명령이 사용하는 `/bin/sh`를 포함해야 한다. 예를 들어 `registry.access.redhat.com/ubi9/ubi-micro:9.6`을 base로 사용하고 ONNX 파일을 `/models/model.onnx`에 복사한다. `scratch` image는 pull에는 성공해도 modelcar container 생성 단계에서 실패한다.

```bash
REGISTRY=$(oc get cm exam-provided-registry-inputs -n ex267-t06-registry -o jsonpath='{.data.oci_registry}')
REGISTRY_USER=$(oc get secret exam-provided-oci-credentials -n ex267-t06-registry -o jsonpath='{.data.username}' | base64 -d)
oc get secret exam-provided-oci-credentials -n ex267-t06-registry -o jsonpath='{.data.password}' \
  | base64 -d | podman login --tls-verify=false --username "$REGISTRY_USER" --password-stdin "$REGISTRY"
unset REGISTRY_USER
```

Secret, token, API 응답 본문은 ConfigMap에 넣지 않는다.

```bash
../../exam-lab.sh grade 06
```

