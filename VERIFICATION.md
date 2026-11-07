# 실습 환경 검증 요약

최종 검증일: 2026-11-07 (Asia/Seoul)

이 문서는 공개 가능한 검증 결과만 기록한다. 대상 클러스터 주소, 로그인 정보, Secret 값과 내부 API 응답 본문은 저장하지 않는다.

## 결론

기존 10개 문제는 유지했고, V2.13 번호형 Markdown 34개를 모두 문제 지침·환경 준비·실제 리소스 채점에 연결했다. `ai267 start <task>`는 해당 문제에 필요한 교재 Lab과 `exam-provided-*` 입력만 만들며, 응시자가 완성해야 할 답안 리소스는 만들지 않는다.

`finish`는 만점일 때만 시험 namespace와 활성 교재 Lab을 정리한다. 실패하면 리소스를 보존하므로 수정한 뒤 다시 채점할 수 있다.

## 자동 검증

`./exam-lab.sh validate`로 다음 항목을 확인했다.

- Bash·Python 구문과 86개 YAML 문서 파싱
- 10개 문제의 점수 계약
- Task 01·06·09 부정 fixture와 주요 문제의 정상 fixture
- V2.13 원문 34/34 경로·고정 checksum·채점 ID 매핑
- 문제별 필수 파일과 seed/grader 계약 완전성

## 실제 실습 흐름 검증

| 범위 | 확인 결과 |
| --- | --- |
| Task 01 | 플랫폼 상태는 읽기 전용으로 확인하고, 응시자 Group/Auth/RBAC/S3 작업만 점수에 반영됨을 확인했다. |
| Task 02~04 | `start`가 입력 없이 환경을 준비하고 초기 답안은 0점이며, starter YAML의 server-side dry-run과 cleanup이 성공했다. |
| Task 05 | GPU가 없는 환경에서는 Pending·scheduler 진단까지만 수행하며 가짜 GPU를 만들지 않는다. |
| Task 06 | PVC와 인증된 전용 OCI Registry, kubelet pull Secret이 자동 준비되고 초기 채점은 0/30이었다. 두 ModelCar push/pull, 실제 REST metadata, Ready InferenceService를 만든 뒤 30/30을 확인했다. 존재하지 않는 정상 형식 digest는 06-2에서 실패했고, 원복 후 `finish`가 다시 30/30 및 cleanup을 완료했다. |
| Task 07~08 | 제공 데이터·기준 서비스와 완료 상태 기반 채점 계약을 확인했다. |
| Task 09 | 미완성 RAG baseline은 0/30이고, RBAC·제한 egress·고정 black-box verifier의 10개 동작 검증을 모두 만족하면 30/30임을 확인했다. `finish` cleanup도 확인했다. |
| Task 10 | 제공 모델·sample·lock·replay 입력과 응시자 소유 evidence/rollback 계약을 분리했다. |

## 주요 채점 방어

- 환경의 Operator·Registry 설치 상태만으로 점수를 주지 않는다.
- Task 01은 실제 Group label, Auth allow/admin group, RoleBinding과 제공 S3 값의 일치를 검사한다.
- Task 06은 RHOAI REST의 model/version/artifact ID·metadata, 전용 OCI Registry의 두 실제 manifest digest, Registry ID 라벨이 연결된 Ready InferenceService를 직접 대조한다.
- Task 09는 정확한 Role/RoleBinding/egress NetworkPolicy와 원본 checksum이 고정된 verifier Job의 실제 성공을 요구한다.
- Secret, token, 원문 API 응답은 evidence ConfigMap에 저장하지 않는다.

## 남은 물리적 제한

GPU node가 없는 클러스터에서는 Task 05의 실제 vLLM GPU streaming과 성능 기준선만 완전 검증할 수 없다. 나머지 문제는 제공 Lab 또는 합성 데이터·서비스로 시작, 초기 실패, 정상 성공과 정리를 검증했다.
