# 교재 Lab 기반 시험 환경

이 기능은 **문제·배점·정답·채점 기준을 바꾸지 않는다.** 교재의 검증된 예제를 별도 `ai267-chXX-*` namespace에 준비해, 응시자가 OpenShift AI 3.3의 정상 리소스 형태와 동작을 확인한 다음 기존 `ex267-*` 시험 namespace에서 문제를 풀도록 돕는다.

## 사용 순서

```bash
oc login https://api.<cluster>:6443

bash install-ai267.sh
ai267 start 01
# 웹 문제의 요구 사항 수행
ai267 inspect 01
ai267 finish 01
```

`finish`는 만점일 때만 리소스를 자동 정리한다. 부분 점수나 실패가 있으면 수정과 재채점을 위해 리소스를 보존한다.

단축 명령을 설치하지 않는 경우에만 아래 원본 명령을 사용한다.

```bash

./exam-lab.sh lab-env list
./exam-lab.sh lab-env switch 01
./exam-lab.sh preflight-all
./exam-lab.sh prepare-all
./exam-lab.sh status-all
```

한 문제만 연습할 때는 다음처럼 실행한다.

```bash
./exam-lab.sh lab-env switch 04
./exam-lab.sh prepare 04
./exam-lab.sh grade 04
```

Task 01·02·03의 교재 환경은 MinIO를 사용한다. 자격 증명은 저장소에 넣지 말고 실행 시에만 환경 변수로 전달한다.

```bash
read -rsp 'MinIO access key: ' MINIO_ACCESS_KEY; export MINIO_ACCESS_KEY; echo
read -rsp 'MinIO secret key: ' MINIO_SECRET_KEY; export MINIO_SECRET_KEY; echo
./exam-lab.sh lab-env switch 03
unset MINIO_ACCESS_KEY MINIO_SECRET_KEY
```

## 문제별 연결

| Task | 교재 기준 환경 | 목적 |
| --- | --- | --- |
| 01·02 | Chapter 02 | S3 connection, Workbench, PVC, custom image의 정상 예시 |
| 03 | Chapter 06 | DSPA, KFP v2, object storage의 정상 예시 |
| 04 | Chapter 04 | KServe V2 inference와 OCI ModelCar의 정상 예시 |
| 07 | Chapter 05 | TrustyAI capture, reference data, drift request의 정상 예시 |
| 08 | Chapter 08 | CPU 양자화 결과와 LMEvalJob server-side schema 검증 |
| 09 | Chapter 09 | mock LLM, RAG, read-only tool, guardrail의 정상 예시 |

Task 05는 물리 GPU가 필요하므로 교재 환경으로 GPU를 대신 만들지 않는다. Task 06은 현재 클러스터의 Model Registry가 `Removed`이므로 기존 metadata·계보·배포 연결 증적 계약을 유지한다. Task 10은 앞선 문제의 결과를 연결하는 통합 과제라 별도 기준 환경을 만들지 않는다.

## 상태 확인과 정리

```bash
./exam-lab.sh lab-env status all
./exam-lab.sh lab-env cleanup all --yes
./exam-lab.sh cleanup-all --yes
```

두 namespace 집합은 분리되어 있으므로 교재 기준 환경이 시험 정답을 자동 완성하지 않는다.

## 한 번에 하나만 실행

교재 Lab은 동시에 여러 개를 준비하지 않는다. 다음 문제로 이동할 때 `switch`를 실행하면 이전 `ai267-chXX-*` namespace를 먼저 정리하고 선택한 문제의 Lab 하나만 준비한다. Chapter 02의 공용 이미지 카탈로그와 Chapter 06·07의 MinIO bucket은 전환 중 보존한다.

```bash
./exam-lab.sh lab-env switch 03
# Task 03 연습

./exam-lab.sh lab-env switch 04
# Chapter 06 환경 정리 후 Chapter 04 환경 준비
```

`lab-env prepare all`은 의도적으로 거부된다.

인증서 kubeconfig처럼 `oc whoami -t`가 토큰을 반환하지 않는 환경에서는 Chapter 02의 Workbench OAuth URL 검사 대신 Workbench Pod Ready를 확인한다. PVC, S3 Connection, 커스텀 이미지 빌드와 카탈로그 등록은 그대로 수행한다.
