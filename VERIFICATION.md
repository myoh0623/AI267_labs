# 검증 기록

기준일: 2026-11-07 (Asia/Seoul)

대상: AI267 3.3 교실용 원격 워크스테이션(공개 문서에서는 접속 주소 생략)

## 확인된 플랫폼

- `oc whoami`: `admin`
- Red Hat OpenShift AI CSV: `rhods-operator.3.3.1`, `Succeeded`
- Lab CLI: `/usr/local/bin/lab`
- 설치 과정: AI267 계열 3.3.0 course
- API: `HardwareProfile v1`, `Notebook v1`, `DSPA v1`, `Pipeline/PipelineVersion v2beta1`, `InferenceService v1beta1`

EPUB에서 다음 공식 Lab 이름을 직접 확인했고 원격 `lab status`에서도 모두 인식되었다.

```text
intro-projects
workbench-creating
workbench-connections
workbench-working
workbench-custom
serving-openvino
dspa-intro
dspa-kubeflow
dspa-elyra
```

`workbench-creating`은 실제로 빈 상태에서 `lab start` 후 `lab finish`를 실행해 프로젝트 생성과 정리를 확인했다. 최종 상태는 `Finished`였고 프로젝트가 삭제되었다.

`serving-openvino`은 start 후 Connection Secret의 3.3 label/annotation과 Workbench 환경을 확인하고 finish했다. 표준 라이브러리 SigV4 helper는 격리된 임시 bucket에서 create/upload/download/byte-compare/purge/delete를 모두 통과했으며, 공식 Lab과 임시 bucket은 남지 않았다.

`workbench-connections`은 start 후 실제 Pod container가 `workbench-connections-wb`와 `kube-rbac-proxy`임을 확인했다. `-c workbench-connections-wb`로 `/opt/app-root/src`에 입력 파일을 쓰고 읽는 smoke test가 성공했으며, 임시 파일을 지운 뒤 Lab을 finish했다. 최종 상태는 `Finished`이고 namespace가 남지 않았다.

## 구현 검증 범위

- wrapper가 공식 Lab project를 직접 사용하고 `ex267-*` namespace를 만들지 않는지
- 다른 문제가 Started 상태일 때 다음 문제 시작을 거부하는지
- 실패한 채점에서 Lab을 보존하고 만점에서만 finish하는지
- Task 02의 Auth/전체 Group/ClusterRoleBinding backup이 모두 유효할 때만 복구하고, 불완전한 state에서는 아무 전역 변경도 하지 않는지
- Task 08·09·11의 공용 S3 helper가 task-created bucket의 무작위 ownership object를 검증하고, 누락·불일치 시 purge/delete 없이 fail-closed하는지
- S3 fixture cleanup이 공식 Lab의 MinIO 의존성이 살아 있는 동안 먼저 실행되고, 실패하면 공식 Lab과 recovery state를 보존하는지
- Task 10이 기존 가상환경 경로를 거부하고 exact task-owned marker가 있을 때만 recursive delete하는지
- Task 05 채점 Job이 중지된 Workbench PVC를 read-only로만 mount하고, exact ownership을 확인한 뒤 성공·실패 모두에서 삭제되는지
- Task 12 compatibility Secret이 공식 `s3-minio`의 네 값만 복제하고 task ownership marker가 있을 때만 정리되는지
- 각 grader가 공식 Lab baseline만으로 100점을 주지 않는지
- 17개 첨부 파일이 SOURCE-MAP에 정확히 한 번씩 대응하는지

## 최종 검증 결과

- `./exam-lab.sh validate`: PASS
  - 12개 Task와 각 5개 채점 항목(총 60개) 계약 확인
  - grader 회귀 테스트 22개 PASS
  - fixture 정리 안전성 테스트 5개 PASS
  - Lab start/finish/reset 수명주기 회귀 테스트 PASS
  - 첨부 문서 17/17 mapping 확인
- `git diff --check`: PASS

위의 세 Lab에 대한 실제 start/finish smoke test는 변경 전 원격 세션에서 완료했다. 최종 변경본을 대상으로 한 전체 Task 원격 smoke test는 워크스테이션이 오프라인이어서 실행하지 못했다. 마지막으로 직접 시작했던 `dspa-kubeflow`의 종료 상태도 같은 이유로 재확인하지 못했으므로, 워크스테이션이 다시 온라인이 되면 다음 명령으로 먼저 정리 상태를 확인한다.

```bash
lab status dspa-kubeflow
cd && lab finish dspa-kubeflow
```

정적·회귀 테스트는 실제 OpenShift API, Dashboard 조작, Pipeline run과 model inference를 대체하지 않는다. 나머지 Task의 end-to-end 확인은 해당 교실 클러스터에서 순서대로 `ai267 NN` → 풀이 → `ai267 grade NN` → `ai267 finish NN`을 실행해 완료해야 한다.

Task 06 채점은 두 local tag가 같은 image인지, `custom-workbench-image:1.0` remote import가 성공했는지, 실제 Workbench에서 package가 동작하는지까지 확인한다. 독립형 교실 registry의 인증·인증서에 의존하는 `custom-workbench:1.0` 첫 번째 tag의 remote manifest 자체는 자동 채점하지 않으므로, 해당 push 명령의 성공 출력은 실습자가 별도로 확인한다.
