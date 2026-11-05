# 실제 클러스터 검증 결과

검증일: 2026-11-05 (Asia/Seoul)

대상: `student@100.94.27.27`, OpenShift 4.20.14 / OpenShift AI 3.3.1

## 결론

문제와 채점 대상 리소스는 변경하지 않고, `ai267 start <task>`가 필요한 교재 Lab과 `exam-provided-*` 입력만 준비하도록 보완했다. 합성 데이터·코드·모델은 입력 자료이며 답안 Secret, InferenceService, LMEvalJob, evidence 값은 응시자가 직접 완성한다.

현재 클러스터의 유일한 물리적 제한은 GPU node가 0개라는 점이다. 따라서 Task 05의 YAML·Pending·scheduler 진단은 수행할 수 있지만 실제 vLLM GPU streaming과 성능 기준선은 GPU가 있는 환경에서만 만점 검증할 수 있다.

## 문제별 검증

| Task | 자동 제공 환경 | 실제 확인 결과 |
| --- | --- | --- |
| 01 | 전용 MinIO, identity 계약 | 기존 `ex267-fraud`를 보존하고 `developer1`이 로그인 계정이 아닌 RBAC subject임을 제공했다. |
| 02 | Chapter 02, 합성 TensorBoard 코드 | 교재 Workbench Pod Ready, 2Gi PVC Bound, custom image build/push 완료. 시험 10Gi PVC와 입력 코드 생성 확인. |
| 03 | Chapter 06, 합성 CSV, KFP v2 소스, DB Secret | 교재 Workflow `Succeeded`; 시험 namespace에서 제공 MinIO 값만으로 DSPA의 모든 condition과 `Ready=True` 확인. 소스는 KFP 2.15.2로 compile 확인. |
| 04 | ONNX v2/v1, SHA-256, `kserve-ovms`, storage bridge | `fraud-v2` InferenceService `Ready=True`; OpenVINO KServe V2 infer가 HTTP 200과 FP32 `[1,2]` 응답 반환. |
| 05 | 실제 GPU node 수 | `gpu_node_count=0`, `full_runtime_possible=false`; 의도된 Pending과 scheduler 진단 경로 확인. 가짜 GPU는 만들지 않음. |
| 06 | `serving-modelregistry` 교재 Lab | Model Registry component `Managed`, `redhattraining-model-registry` `Available=True`, MariaDB/Registry Pod 실행 확인. |
| 07 | Chapter 05, Iris 기준 모델·client·reference | 교재 환경과 시험 namespace의 `iris-monitor`, runtime, client가 Ready 상태임을 확인. |
| 08 | 합성 completions API, 고정 OpenBookQA/GPT-2 offline cache, 한국어·안전 Unitxt recipe | CDN에 의존하지 않고 baseline/optimized가 모두 `Complete/Succeeded`; custom 실행에서 OpenBookQA, `tr_0` 한국어, `tr_1` 안전 결과 JSON 생성 확인. |
| 09 | vendor mock LLM, read-only tool, RAG 앱, ACL 입력 | 세 Deployment 1/1 Ready, `genai-app` Route 생성 확인. namespace 생성 직후 조회 경합에는 상태 재시도를 추가. |
| 10 | current/previous 합성 모델, sample, lock, replay 코드, MinIO 사본 | ConfigMap 7개 입력과 전용 MinIO bucket 생성 확인. replay Job과 evidence는 응시자 작업으로 유지. |

## 채점기 보강

- Task 04는 data connection의 `opendatahub.io/connection-path`와 RHOAI가 주입한 `model.storage.path`를 실제 저장 경로로 인정한다.
- Task 05는 고정 digest·증적만으로 통과하지 않으며 실제 Ready vLLM workload를 요구한다.
- Task 06은 실행 중인 Available Model Registry가 있어야 첫 항목을 통과한다.
- Task 08은 이름만 있는 두 CR이 아니라 결과가 존재하는 `Complete/Succeeded` LMEvalJob 두 개를 요구한다.
- Task 09는 임의 RoleBinding이 아니라 `rag-app` ServiceAccount에 연결된 비관리자 RoleBinding과 NetworkPolicy를 요구한다.

## 안전한 실행 흐름

교재 Lab은 한 번에 하나만 실행한다.

```bash
ai267 start 03
ai267 inspect 03
# 웹 문제를 직접 해결
ai267 finish 03
```

`finish`는 만점일 때만 시험 namespace와 활성 Lab을 정리한다. 실패하면 수정할 수 있도록 그대로 보존한다. Task 01의 기존 사용자 작업은 이번 통합 검증에서 삭제하거나 초기화하지 않았다.
