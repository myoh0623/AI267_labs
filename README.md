# EX267 v3.3 실습형 연습 환경

웹 모의시험의 10개 과제를 실제 OpenShift/OpenShift AI 리소스로 연습하기 위한 문제별 실습 묶음이다. `ai267/v3.3/labs`의 검증된 리소스 형태를 참고했지만, 강의 시연과 달리 초기 상태를 일부러 미완성으로 만들고 응시자가 수정한 결과를 자동 채점한다.

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

`start`는 기존 교재 Lab 정리, 필요한 Lab 실행, 시험 namespace 준비와 초기 상태 확인을 한 번에 처리한다. `finish`는 채점에 통과하면 시험·교재 리소스를 정리하고, 실패하면 수정할 수 있도록 그대로 보존한다. `KUBECONFIG=$HOME/.auth/lab-kubeconfig`와 설치 경로는 자동으로 적용된다.

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

`lab-env`는 문제를 바꾸거나 정답을 적용하지 않는다. 교재의 정상 예제를 별도 `ai267-chXX-*` namespace에 한 번에 하나만 준비하고, 시험은 기존 `ex267-*` namespace에서 그대로 진행한다. 다음 문제로 이동할 때는 `lab-env switch <task>`를 사용한다. 필요한 문제와 Chapter 연결, MinIO 자격 증명 입력 방법은 [LAB-ENVIRONMENT.md](LAB-ENVIRONMENT.md)를 참고한다.

`grade`는 부분 점수를 보여주며, 모든 항목을 통과하지 못하면 종료 코드 1을 반환한다. 자동화에서 결과만 필요하면 `--json`을 추가한다.

## 문제별 프로젝트

| 문제 | 실습 | 기본 프로젝트 | 점수 |
| --- | --- | --- | ---: |
| 01 | 프로젝트·RBAC·S3 연결 | `ex267-fraud` | 24 |
| 02 | Workbench·PVC·실험 증적 | `ex267-t02-workbench` | 30 |
| 03 | KFP v2 Pipeline·실험 비교 | `ex267-t03-pipeline` | 36 |
| 04 | OpenVINO KServe 모델 서빙 | `ex267-t04-serving` | 36 |
| 05 | vLLM·GPU 배치 진단 | `ex267-t05-vllm` | 30 |
| 06 | Model Registry·계보 | `ex267-t06-registry` | 30 |
| 07 | TrustyAI·플랫폼 모니터링 | `ex267-t07-monitoring` | 30 |
| 08 | LLM 최적화·LMEval | `ex267-t08-evaluation` | 24 |
| 09 | Guardrailed RAG | `ex267-t09-rag` | 36 |
| 10 | 재현·증적·롤백 | `ex267-t10-evidence` | 24 |

## 설계 원칙

- `prepare`는 프로젝트와 입력 계약만 생성하며 정답 리소스를 완성하지 않는다.
- 고급 CRD, GPU, object storage, Model Registry endpoint는 클러스터마다 다르므로 `preflight`가 설치 여부를 먼저 보여준다.
- 외부 자격 증명은 Git에 저장하지 않는다. S3/Registry 값은 Console에서 Secret에 입력한다.
- 일부 외부 시스템 결과는 정해진 이름의 `*-evidence` ConfigMap에 digest·ID·HTTP 상태만 기록한다. 실제 Secret이나 원문 데이터는 기록하지 않는다.
- `cleanup`은 `ex267.practice/managed=true`와 해당 문제 번호 라벨이 모두 일치하는 프로젝트만 삭제한다.
- Task 09의 소형 mock 애플리케이션은 원격 AI267 자료에 Chapter 09가 없을 때 `vendor/` 복사본을 사용한다.

각 문제의 정확한 리소스 이름과 evidence key는 `tasks/<문제>/README.md`에 있다.

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

