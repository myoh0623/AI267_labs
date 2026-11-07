# 실제 클러스터 검증 결과

기준 클러스터 검증일: 2026-11-05 (Asia/Seoul)<br>
번호형 실습 완전 반영 검증일: 2026-11-06 (Asia/Seoul)
채점 계약 재검증일: 2026-11-07 (Asia/Seoul)

대상: 전용 AI267 실습 클러스터, OpenShift 4.20.14 / OpenShift AI 3.3.1

## 결론

기존 10개 문제를 유지하면서 V2.13 번호형 Markdown 34개를 모두 추적했다. 누락된 실습 행동은 Task 01~04에 추가하고 실제 리소스·evidence 채점으로 연결했다. `ai267 start <task>`는 필요한 교재 Lab과 `exam-provided-*` 입력만 준비한다. 합성 데이터·코드·모델은 입력 자료이며 답안 Group/Auth, Workbench/Image/Git/S3, Pipeline/Schedule/Elyra, ServingRuntime/InferenceService/인증 evidence는 응시자가 직접 완성한다.

2026-11-06 변경분은 로컬 Bash/Python/YAML/채점 계약/34개 source coverage 검증을 통과했다. 같은 변경분을 실제 클러스터의 별도 검증 checkout에 복사해 Task 02~04의 `start`, 의도된 0점 초기 채점, `cleanup`과 신규 starter YAML server-side dry-run을 확인했다. Task 03 교재 Workflow는 `Succeeded`, Task 04 교재 ModelCar 추론은 HTTP 200이었다. Task 01은 기존 응시 리소스를 덮어쓰지 않고 플랫폼·Auth·DSC를 읽기 전용으로 검사했다.

채점기의 모든 신규 성공 분기는 합성 Kubernetes API 응답을 사용하는 positive fixture로 통과시켰다. 이 검증은 환경 준비가 답안을 미리 완성하지 않으며, 응시자가 요구 리소스를 만들었을 때만 각 항목이 통과한다는 계약까지 포함한다.

현재 클러스터의 유일한 물리적 제한은 GPU node가 0개라는 점이다. 따라서 Task 05의 YAML·Pending·scheduler 진단은 수행할 수 있지만 실제 vLLM GPU streaming과 성능 기준선은 GPU가 있는 환경에서만 만점 검증할 수 있다.

## 문제별 검증

| Task | 자동 제공 환경 | 실제 확인 결과 |
| --- | --- | --- |
| 01 | 전용 MinIO, identity/platform 계약 | CSV `rhods-operator.3.3.1` Succeeded, `default-dsc` Ready/Managed와 cluster-scoped Auth API를 읽기 전용으로 확인했다. 기존 `ex267-fraud`는 보존했고 초기 채점은 답안 미완료로 실패했다. |
| 02 | Chapter 02, custom image source, HardwareProfile starter, 합성 Git/S3/TensorBoard 입력 | MinIO 입력 없이 자동 시작, 교재 custom image build 완료, 시험 입력 생성, 신규 starter dry-run 성공, 10개 항목 모두 의도된 초기 실패, cleanup과 culler 원상복구 확인. |
| 03 | Chapter 06, KFP·Elyra 소스, 합성 CSV, DB Secret | 교재 DSPA Ready와 Workflow Succeeded, 시험 입력 생성, Elyra starter dry-run 성공, 9개 항목 모두 의도된 초기 실패, cleanup 확인. 직접 `lab-env`를 실행해도 MinIO prompt가 생기지 않도록 보완했다. |
| 04 | ONNX v2/v1, Custom ServingRuntime·인증 starter, storage bridge | 교재 ModelCar V2 infer HTTP 200, 시험 입력 생성, runtime/auth starter dry-run 성공, 9개 항목 모두 의도된 초기 실패, cleanup 확인. |
| 05 | 실제 GPU node 수 | `gpu_node_count=0`, `full_runtime_possible=false`; 의도된 Pending과 scheduler 진단 경로 확인. 가짜 GPU는 만들지 않음. |
| 06 | `serving-modelregistry` 교재 Lab | Model Registry component `Managed`, `redhattraining-model-registry` `Available=True`, MariaDB/Registry Pod 실행 확인. CR API는 v1beta1, 실제 metadata REST는 Service `http-api`의 v1alpha3임을 실측했다. |
| 07 | Chapter 05, Iris 기준 모델·client·reference | 교재 환경과 시험 namespace의 `iris-monitor`, runtime, client가 Ready 상태임을 확인. |
| 08 | 합성 completions API, 고정 OpenBookQA/GPT-2 offline cache, 한국어·안전 Unitxt recipe | CDN에 의존하지 않고 baseline/optimized가 모두 `Complete/Succeeded`; custom 실행에서 OpenBookQA, `tr_0` 한국어, `tr_1` 안전 결과 JSON 생성 확인. |
| 09 | vendor mock LLM, 쓰기 가능한 미완성 tool, RAG 앱, ACL 입력, 고정 verifier | 세 Deployment 1/1 Ready와 `genai-app` Route를 제공하되 답안 Role/RoleBinding/NetworkPolicy와 ACL·streaming·read-only 동작은 만들지 않는다. |
| 10 | current/previous 합성 모델, sample, lock, replay 코드, MinIO 사본 | ConfigMap 7개 입력과 전용 MinIO bucket 생성 확인. replay Job과 evidence는 응시자 작업으로 유지. |

## 채점기 보강

- Task 04는 data connection의 `opendatahub.io/connection-path`와 RHOAI가 주입한 `model.storage.path`를 실제 저장 경로로 인정한다.
- Task 05는 고정 digest·증적만으로 통과하지 않으며 실제 Ready vLLM workload를 요구한다.
- Task 06은 환경의 Registry Available 상태를 점수로 주지 않는다. 실제 REST API의 `fraud-risk`, 1.0.0/1.1.0 ID, artifact URI/digest, metadata와 Registry ID 라벨이 연결된 Ready InferenceService를 직접 대조한다.
- Task 08은 이름만 있는 두 CR이 아니라 결과가 존재하는 `Complete/Succeeded` LMEvalJob 두 개를 요구한다.
- Task 09는 정확한 `rag-reader` rules, `rag-app` 전용 RoleBinding, 목적지가 제한된 Egress NetworkPolicy와 원본 checksum을 확인한 고정 black-box verifier Job 성공을 요구한다.

## 안전한 실행 흐름

교재 Lab은 한 번에 하나만 실행한다.

```bash
ai267 start 03
ai267 inspect 03
# 웹 문제를 직접 해결
ai267 finish 03
```

`finish`는 만점일 때만 시험 namespace와 활성 Lab을 정리한다. 실패하면 수정할 수 있도록 그대로 보존한다. Task 01의 기존 사용자 작업은 이번 통합 검증에서 삭제하거나 초기화하지 않았다.
