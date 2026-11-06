# EX267 v3.3 실습형 연습 환경

웹 모의시험의 기존 10개 과제를 실제 OpenShift/OpenShift AI 리소스로 연습하기 위한 문제별 실습 묶음이다. 기존 문제를 삭제하거나 다른 문제로 교체하지 않고, AI267 3.3 교재 Lab과 공개 EX267-V2.13 디렉터리의 번호형 Markdown 34개를 준비 리소스·문제 지침·채점·정리에 모두 연결했다. 강의 시연과 달리 초기 상태를 일부러 미완성으로 만들고 응시자가 수정한 실제 결과를 자동 채점한다.

- GitHub: https://github.com/myoh0623/AI267_labs

```bash
git clone https://github.com/myoh0623/AI267_labs.git
cd AI267_labs
./exam-lab.sh validate
```

## 빠른 시작

```bash
bash install-ai267.sh

# 이후 문제마다 세 명령만 사용
ai267 start 04
# 웹 문제의 지침대로 수행
ai267 inspect 04
ai267 finish 04
```

`start`는 기존 교재 Lab 정리, 필요한 Lab 실행, 시험 namespace 준비, 합성 데이터·입력 코드·기준 런타임 제공과 초기 상태 확인을 한 번에 처리한다. MinIO가 필요한 문제는 클러스터의 자격 증명을 자동으로 읽으므로 별도 입력 프롬프트가 없다. Task 01·02·03·04·08·10에는 전용 bucket과 `exam-provided-minio` Secret이 시험 제공값으로 생성되지만, 채점 대상 S3 Secret과 답안 리소스는 일부러 미완성으로 남겨 응시자가 직접 구성한다. `finish`는 채점에 통과하면 시험·교재 리소스를 정리하고, 실패하면 수정할 수 있도록 그대로 보존한다. Task 01의 Dashboard Auth와 Task 02의 cluster-wide culler 설정은 시작 시 백업되어 정리할 때 원래 값으로 복원된다. `KUBECONFIG=$HOME/.auth/lab-kubeconfig`와 설치 경로는 자동으로 적용된다.

전체 원본 명령이 필요한 경우:

```bash
oc login https://api.<cluster>:6443
cd AI267_labs

./exam-lab.sh list
./exam-lab.sh preflight-all
./exam-lab.sh lab-env switch 01
./exam-lab.sh prepare-all
./exam-lab.sh status-all

# 10개 문제를 푼 뒤 전체 채점
./exam-lab.sh grade-all

# 모든 전용 프로젝트 제거
./exam-lab.sh cleanup-all --yes

# 한 문제만 연습하는 경우
./exam-lab.sh preflight 01
./exam-lab.sh prepare 01
./exam-lab.sh status 01

# OpenShift Console에서 과제를 수행한 뒤
./exam-lab.sh grade 01

# 해당 문제의 전용 프로젝트만 제거
./exam-lab.sh cleanup 01 --yes
```

`lab-env`는 문제를 바꾸거나 정답을 적용하지 않는다. 교재의 정상 예제를 별도 `ai267-chXX-*` namespace에 한 번에 하나만 준비하고, 시험은 기존 `ex267-*` namespace에서 그대로 진행한다. 다음 문제로 이동할 때는 `lab-env switch <task>`를 사용한다. 필요한 문제와 Chapter 연결, 자동으로 제공되는 입력값은 [LAB-ENVIRONMENT.md](LAB-ENVIRONMENT.md)를 참고한다.

`grade`는 부분 점수를 보여주며, 모든 항목을 통과하지 못하면 종료 코드 1을 반환한다. 자동화에서 결과만 필요하면 `--json`을 추가한다.

## 문제별 프로젝트

| 문제 | 실습 | 기본 프로젝트 | 점수 |
| --- | --- | --- | ---: |
| 01 | 사용자·프로젝트·S3 | `ex267-fraud` | 21 |
| 02 | Workbench·이미지·Git·S3 | `ex267-t02-workbench` | 30 |
| 03 | KFP·Elyra Pipeline·예약 실행 | `ex267-t03-pipeline` | 36 |
| 04 | OpenVINO·Custom Runtime·인증 | `ex267-t04-serving` | 36 |
| 05 | vLLM·GPU 배치 진단 | `ex267-t05-vllm` | 30 |
| 06 | Model Registry·계보 | `ex267-t06-registry` | 30 |
| 07 | TrustyAI·플랫폼 모니터링 | `ex267-t07-monitoring` | 30 |
| 08 | LLM 최적화·LMEval | `ex267-t08-evaluation` | 24 |
| 09 | Guardrailed RAG | `ex267-t09-rag` | 30 |
| 10 | 재현·증적·롤백 | `ex267-t10-evidence` | 24 |

## 설계 원칙

- `prepare`는 프로젝트와 입력 계약만 생성하며 정답 리소스를 완성하지 않는다. `ai267 start`가 별도 `exam-provided-*` 리소스로 합성 데이터, 코드, 모델과 기준 서비스를 추가한다.
- 고급 CRD, GPU와 object storage는 클러스터마다 다르므로 `preflight`가 설치 여부를 먼저 보여준다. Task 06은 교재 `serving-modelregistry` Lab을 시작해 Registry 선행 환경을 구성한다.
- 외부 자격 증명은 Git에 저장하지 않는다. 실습 클러스터의 MinIO 값은 실행 중에만 읽어 문제 namespace의 `exam-provided-minio`로 제공하며, 응시자가 이를 채점 대상 Secret에 적용한다.
- 일부 외부 시스템 결과는 정해진 이름의 `*-evidence` ConfigMap에 digest·ID·HTTP 상태만 기록한다. 실제 Secret이나 원문 데이터는 기록하지 않는다.
- `cleanup`은 `ex267.practice/managed=true`와 해당 문제 번호 라벨이 모두 일치하는 프로젝트만 삭제한다.
- [V213-COVERAGE.md](V213-COVERAGE.md), [source-coverage.yaml](source-coverage.yaml), [source-inventory.sha256](source-inventory.sha256)은 고정 commit의 원본 Markdown 34개 전부에 대한 문제/채점 대응과 원문 checksum을 명시한다. `validate`가 개수, 경로, checksum 목록, 중복과 잘못된 채점 ID를 검사한다.
- V2.13의 size selector는 3.3 `HardwareProfile`, 제거된 ModelMesh Multi-model은 지원되는 3.3 KServe `RawDeployment`로 대응한다. 학습 목표는 유지하고 폐기된 구성 요소를 재설치하지 않는다.
- Task 09의 소형 mock 애플리케이션은 원격 AI267 자료에 Chapter 09가 없을 때 `vendor/` 복사본을 사용한다.
- 현재 클러스터에는 GPU node가 없으므로 Task 05의 실제 vLLM 처리량 측정만 완전 수행할 수 없다. 가짜 GPU를 만들지 않고 Pending·scheduler 진단을 연습한다.

## 자동 제공되는 입력

| Task | `ai267 start`가 준비하는 선행 입력 |
| --- | --- |
| 01 | MinIO bucket/credential, identity/Auth 복원 계약 |
| 02 | MinIO, Custom Image source, 불완전 `git-experiments`, TensorBoard 코드, culler 복원본 |
| 03 | MinIO 합성 CSV, DSPA DB Secret, KFP v2·Elyra source와 5분 schedule 계약 |
| 04 | 교재 ONNX v2/v1, SHA-256, 공식 OpenVINO runtime, 2.13→3.3 serving 호환 계약 |
| 05 | 실제 GPU node 수와 실행 가능 여부 |
| 06 | 교재 Model Registry/MariaDB/OCI registry/ONNX 자산 |
| 07 | Iris 기준 모델, client, versioned reference dataset |
| 08 | baseline/optimized mock completions Service, OpenBookQA/GPT-2 offline cache, 한국어·안전 Unitxt recipe |
| 09 | mock RAG 앱과 source/revision/ACL 계약 |
| 10 | current/previous model, sample, lock, replay 코드와 MinIO 사본 |

`exam-provided-*`는 시험지에서 주어지는 입력 자료에 해당한다. 이를 읽고 채점 대상 리소스에 반영하는 과정은 응시자의 작업이다.

각 문제의 정확한 리소스 이름과 evidence key는 `tasks/<문제>/README.md`에 있다.

실제 클러스터에서 수행한 시작·실패 보존·만점 채점·자동 정리 결과와 환경 제약은 [VERIFICATION.md](VERIFICATION.md)에 기록되어 있다.

## 로컬 정적 검증

클러스터 로그인 없이 스크립트 문법, Python 채점기, YAML 구조를 검사할 수 있다.

```bash
./exam-lab.sh validate
```

실제 RHOAI 동작 여부는 대상 클러스터에서 `prepare`와 `grade`로 검증해야 한다.

## 원격 학습 서버

스크립트는 AI267 3.3 자료를 `AI267_V33_ROOT`, `~/ai267-v3.3`, `~/course` 순서로 찾는다. 관리용 kubeconfig가 별도 파일에 있다면 명령 앞에 `KUBECONFIG=/path/to/kubeconfig`를 지정한다.

```bash
KUBECONFIG="$HOME/.auth/lab-kubeconfig" ./exam-lab.sh preflight-all
KUBECONFIG="$HOME/.auth/lab-kubeconfig" ./exam-lab.sh prepare-all
```

