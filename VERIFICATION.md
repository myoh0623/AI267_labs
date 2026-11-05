# 통합 검증 결과

검증일: 2026-11-05 (Asia/Seoul)

대상: `student@100.94.27.27`, OpenShift 4.20 / OpenShift AI 3.3.1

## 실행 흐름

10개 Task 모두 다음 동작을 검사했다.

1. `ai267 start <task>`로 필요한 교재 Lab과 시험 seed 준비
2. 미완성 상태의 채점 실패
3. 채점 실패 후 시험 namespace 보존
4. 통과 fixture 적용 후 전체 점수 판정
5. `ai267 finish <task>` 통과 후 namespace 자동 정리

Task 01·02는 인증서 kubeconfig에서 `oc whoami -t`를 사용할 수 없는 환경을 위해 Workbench Pod Ready 검증 경로를 추가했다. Task 08은 LMEvalJob finalizer와 Pending 평가 Pod가 namespace 종료를 지연하지 않도록 사전 정리를 추가했다.

| Task | 시작 | 미완성 실패·보존 | 만점 채점 | 자동 정리 | 비고 |
| --- | --- | --- | --- | --- | --- |
| 01 | PASS | PASS | 24/24 | PASS | Chapter 02 인증서 kubeconfig 호환 |
| 02 | PASS | PASS | 30/30 | PASS | Workbench·PVC 계약 |
| 03 | PASS | PASS | 36/36 | PASS | DSPA와 실제 Workflow 실행 |
| 04 | PASS | PASS | 36/36 계약 테스트 | 공통 정리 경로 검증 | Lab ModelCar Ready 확인; 실제 OpenVINO/S3 모델은 환경값 필요 |
| 05 | PASS | PASS | 30/30 | PASS | GPU 없음: Pending·스케줄링 계약 기준 |
| 06 | PASS | PASS | 30/30 | PASS | Registry Removed: metadata 증적 계약 기준 |
| 07 | PASS | PASS | 30/30 | PASS | TrustyAIService 상태 계약 |
| 08 | PASS | PASS | 24/24 | PASS | LMEval finalizer 정리 포함 |
| 09 | PASS | PASS | 36/36 | PASS | vendor mock LLM/RAG 배포 포함 |
| 10 | PASS | PASS | 24/24 | PASS | replay Job·rollback 증적 |

## 해석 시 주의

- Task 04의 채점기 만점 계약은 36/36으로 검증했다. 그러나 현재 클러스터에는 문제에서 요구하는 실제 OpenVINO S3 모델 아티팩트가 없으므로, 실제 endpoint 성공은 환경별 모델과 S3 값을 넣은 뒤 확인해야 한다.
- Task 05는 물리 GPU가 없으므로 실제 vLLM GPU 처리량을 검증한 결과가 아니다.
- Task 06은 Model Registry 구성 요소가 `Removed`이므로 실제 v1beta1 API 호출 대신 증적 계약을 검증한 결과다.
- 검증 fixture는 채점기 테스트용이며 교재 실습 결과를 대신하지 않는다.
