# AI267 3.3 Browser Practice Labs

첨부된 Markdown 문제를 입력 순서대로 재구성한 비공식 RHOAI 3.3 연습 환경이다. 설치·이론 문서는 안내로 분리하고, 관련 실습 14개의 고유 요구를 빠뜨리지 않은 채 12개 문제로 묶었다. 각 문제는 AI267 3.3 EPUB의 공식 Guided Exercise Lab을 직접 시작하고, 원문 수행에 필요한 입력만 custom fixture로 보충하며 별도의 `ex267-*` 복제 프로젝트를 만들지 않는다.

GitHub: <https://github.com/myoh0623/AI267_labs>

## 시작

```bash
git clone https://github.com/myoh0623/AI267_labs.git
cd AI267_labs
bash install-ai267.sh

ai267 list
ai267 01
# RHOAI Console에서 문제 해결
ai267 grade 01
ai267 finish 01
```

명령은 네 가지면 충분하다.

- `ai267 NN`: 공식 Lab 시작, 필요한 입력 fixture 준비, 문제 표시
- `ai267 inspect NN`: 현재 Kubernetes/RHOAI 리소스 표시
- `ai267 grade NN`: 실제 결과를 채점한다. Task 05만 중지된 Workbench PVC를 read-only로 검사하는 task-owned 일회성 Job을 만들고 즉시 삭제하며, 나머지 채점은 읽기 전용이다.
- `ai267 finish NN`: 만점이면 공식 `lab finish` 실행과 fixture 원상복구

실패한 `finish`는 Lab을 보존한다. 풀이를 버릴 때만 `ai267 reset NN`을 사용한다. 한 번에 한 문제만 실행할 수 있다.

## 문제

| 번호 | 문제 | 공식 AI267 3.3 Lab |
| --- | --- | --- |
| 01 | 프로젝트 권한과 Workbench | `workbench-creating` |
| 02 | RHOAI 사용자·그룹 접근 제어 | `intro-projects` + 안전한 custom fixture |
| 03 | Hardware Profile과 Git 작업 | `workbench-creating` + profile fixture |
| 04 | S3 Connection과 객체 검증 | `workbench-connections` |
| 05 | 기존 Workbench 수정 | `workbench-working` |
| 06 | Custom Image와 package metadata | `workbench-custom` |
| 07 | Git Notebook 협업 | `workbench-working` |
| 08 | `carido-model.joblib` S3 저장 | `workbench-connections` |
| 09 | OpenVINO `diabetes` 단일 모델 배포 | `serving-openvino` |
| 10 | Kubeflow 5분 Schedule | `dspa-kubeflow` |
| 11 | Pipeline Server와 `carido` 모델 Pipeline | `dspa-intro` |
| 12 | Elyra Pipeline | `dspa-elyra` |

문제 원문과 새 문제의 17/17 대응은 [SOURCE-MAP.md](SOURCE-MAP.md), Lab의 정확한 시작·종료 명령은 [LAB-ENVIRONMENT.md](LAB-ENVIRONMENT.md)에 있다.

## RHOAI 3.3 변환 원칙

- `lab start -t AI26x ...` 대신 EPUB에 인쇄된 `lab start <lab-name>`을 사용한다.
- `RHOAI2.13` 대신 `RHOAI3.3`, Workbench Python 3.12, KFP 2.15.2를 사용한다. 공식 3.3 pipeline CLI 실습은 Python 3.13을 사용한다.
- Workbench size는 제거된 `notebookSizes`가 아니라 `HardwareProfile`로 구성한다.
- 사용자 접근은 가상의 `rhods-user/rhods-admin` ClusterRole이 아니라 `Auth/auth`의 `allowedGroups`와 `adminGroups`로 구성한다.
- Workbench 연결은 `opendatahub.io/connection-type-protocol` annotation이 있는 Connection Secret을 사용한다.
- 3.3에서 제거된 Multi-model/ModelMesh **serving 방식만** KServe RawDeployment/OpenVINO 단일 모델 V2 API로 전환한다. 원문의 `tiger`, `diabetes`, `rhoaiserving-using`, token 인증 비활성 요구는 유지한다.
- 설치·Operator·DataScienceCluster 확인은 [docs/SETUP.md](docs/SETUP.md)의 사전조건이며 채점 문제가 아니다.

## 환경 준비와 답안의 경계

`start`가 만드는 것은 공식 Lab의 입력과 안전한 fixture뿐이다. RoleBinding, Workbench, 문제에서 사용자가 만들도록 한 Project·Connection, Git commit, 결과 모델, InferenceService, Pipeline definition·schedule·run 같은 답안은 사용자가 직접 만든다. Task 01은 User 객체와 전역 Hardware Profile만 제공하며 `my-lab-pro`는 학습자가 만든다. Task 04는 빈 프로젝트만 제공하고 bucket·Connection·Workbench를 모두 학습자가 만든다. 예외적으로 Task 09는 배포할 합성 ONNX 입력을 S3에 제공하고, Task 08과 Task 11은 정리용 숨은 ownership object 외에는 답안 객체가 없는 bucket을 제공한다. Task 08은 Python 입력을, Task 11은 기존 connection 역할의 `my-s3-connection`과 standalone Pipeline component 입력도 제공한다. Task 12는 공식 project·DSPA·S3 입력과 원문 Secret 이름을 위한 compatibility alias만 제공하며 Workbench·Runtime Image·graph는 학습자가 만든다. Task 02는 cluster-scoped `Auth`, 전체 Group 목록, 관련 ClusterRoleBinding을 사용자가 변경하기 전에 로컬 state에 원자적으로 백업하고 `finish/reset`에서 복원한다. start 자체는 전역 접근 설정을 변경하지 않으며 HTPasswd Secret도 수정하지 않는다.

## 검증

```bash
./exam-lab.sh validate
```

정적 검증은 12개 catalog, 17개 source mapping, Bash/Python/YAML, grader point 계약과 금지된 2.13 명령을 검사한다. 실제 클러스터 결과는 [VERIFICATION.md](VERIFICATION.md)에 기록한다.
