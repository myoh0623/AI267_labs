# Task 04 · OpenVINO·Custom Runtime·인증

기존 `fraud-v2` OpenVINO KServe 배포·호출·rollback 문제를 유지한다. 번호형 V2.13 실습의 Multi-model external route/token 및 no-token 동작은 RHOAI 3.3에서 제거된 ModelMesh를 재설치하지 않고, 지원되는 KServe `RawDeployment`의 token on/off 검증으로 수행한다. RHOAI 3.3 교재의 Custom ServingRuntime import도 추가한다.

`ai267 start 04`는 전용 MinIO와 versioned ONNX v2/v1, S3 storage bridge, 공식 `kserve-ovms` 입력 runtime만 준비한다. `fraud-s3`, Custom Runtime, InferenceService, Route/auth 설정, request, rollback은 응시자가 완성한다.

## 수행 목표

1. `exam-provided-model-artifacts`의 v2/v1 URI와 checksum을 확인하고 `fraud-s3`를 실제 S3 connection으로 완성한다.
2. `resources/inferenceservice-starter.yaml`을 사용해 `fraud-v2`를 배포한다. `models/fraud/2/`, ONNX v1, 설치 환경의 OpenVINO runtime, `RawDeployment`, CPU 1/1, memory 2Gi/2Gi를 사용한다.
3. Ready와 URL을 확인하고 KServe V2 정상 request는 2xx, invalid shape request는 4xx가 되는지 확인한다. response body의 SHA-256을 `serving-evidence`에 기록한다.
4. 서비스를 지웠다가 같은 v2 checksum으로 재생성한다. 그다음 `models/fraud/1/`로 rollback해 Ready와 protocol request를 다시 검증하고 rollback SHA를 기록한다.
5. `resources/custom-runtime-starter.yaml`을 완성해 `fraud-custom-runtime`을 import한다. container image는 tag가 아니라 `@sha256:<64 hex>`로 고정하고, protocol `v2`, format `sklearn`, non-root security context를 유지한다. RHOAI **Settings → Models resources and operations → Serving runtimes**에서도 보이는지 확인한다.
6. `fraud-v2`를 external Route로 노출한다. V2.13의 Multi-model 요구를 RHOAI 3.3 `RawDeployment`로 매핑했음을 `serving-mode-evidence.legacy_multimodel_status=mapped-to-rhoai-3.3-rawdeployment`에 기록한다.
7. `resources/inference-auth-starter.yaml`의 `infer-serviceaccount`와 token Secret을 만든다. token authentication을 켠 상태에서 Bearer token 호출이 2xx, token 없는 호출이 401 또는 403인지 검증한다. Secret 평문은 evidence에 쓰지 않는다.
8. 같은 external endpoint에서 token authentication을 끄고 token 없는 호출이 2xx인지 확인한다. protected/public 두 상태의 실제 HTTP code와 Route host를 `serving-mode-evidence`에 기록한다.
9. `custom-runtime-evidence`에는 runtime name, 고정 image digest, `sklearn`, 실제 validation HTTP code를 기록한다.

## Console 위치

- S3 connection: RHOAI **Projects → ex267-t04-serving → Connections**
- Custom runtime: RHOAI **Settings → Models resources and operations → Serving runtimes → Add serving runtime**
- 모델 배포: RHOAI **Projects → ex267-t04-serving → Deployments → Deploy model**
- external route/token: 배포 wizard **Advanced settings → Make deployed models available through an external route / Require token authentication**
- URL/token: 배포 row의 **Internal and external endpoint details**. RHOAI 3.3 RawDeployment token Secret은 모델별로 표시된다.
- 리소스 확인: OpenShift **Networking → Routes**, **Workloads → Secrets**, **Home → Search → InferenceService/ServingRuntime**

`custom-runtime-starter.yaml`은 구조만 제공한다. 승인 image digest를 확인하기 전에는 적용하지 않는다.

```bash
ai267 grade 04
ai267 finish 04
```

