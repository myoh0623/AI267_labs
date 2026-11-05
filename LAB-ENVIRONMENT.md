# 교재 Lab 기반 시험 환경

이 기능은 **문제·배점·정답·채점 기준을 바꾸지 않는다.** 교재의 검증된 예제를 별도 `ai267-chXX-*` namespace에 준비해, 응시자가 OpenShift AI 3.3의 정상 리소스 형태와 동작을 확인한 다음 기존 `ex267-*` 시험 namespace에서 문제를 풀도록 돕는다.

## 사용 순서

```bash
oc login https://api.<cluster>:6443

./exam-lab.sh lab-env list
./exam-lab.sh lab-env prepare all
./exam-lab.sh preflight-all
./exam-lab.sh prepare-all
./exam-lab.sh status-all
```

한 문제만 연습할 때는 다음처럼 실행한다.

```bash
./exam-lab.sh lab-env prepare 04
./exam-lab.sh prepare 04
./exam-lab.sh grade 04
```

Task 01·02·03의 교재 환경은 MinIO를 사용한다. 자격 증명은 저장소에 넣지 말고 실행 시에만 환경 변수로 전달한다.

```bash
read -rsp 'MinIO access key: ' MINIO_ACCESS_KEY; export MINIO_ACCESS_KEY; echo
read -rsp 'MinIO secret key: ' MINIO_SECRET_KEY; export MINIO_SECRET_KEY; echo
./exam-lab.sh lab-env prepare 03
unset MINIO_ACCESS_KEY MINIO_SECRET_KEY
```

## 문제별 연결

| Task | 교재 기준 환경 | 목적 |
| --- | --- | --- |
| 01·02 | Chapter 02 | S3 connection, Workbench, PVC, custom image의 정상 예시 |
| 03 | Chapters 06·07 | DSPA, KFP v2, object storage, 비교 run의 정상 예시 |
| 04 | Chapters 03·04 | KServe V2 inference와 OCI ModelCar의 정상 예시 |
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
