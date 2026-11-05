# EX267-V2.13 번호형 Markdown 완전 반영표

기준 원본은 [`anishrana2001/Openshift` commit `40d6458`](https://github.com/anishrana2001/Openshift/tree/40d6458045d7134c9aa1f15d749325faa3bc6062/EX267-V2.13)의 Markdown **34개 전부**다. 원문의 문제를 복제한 것이 아니라 학습 행동과 고정값을 이 저장소의 기존 10개 문제, RHOAI 3.3 API, 준비/채점/정리 흐름에 대응시켰다. 상세 기계 판독 매핑은 [source-coverage.yaml](source-coverage.yaml), 고정 커밋의 파일별 원문 checksum은 [source-inventory.sha256](source-inventory.sha256)에 있으며 `ai267 validate`가 34개 경로·checksum 목록·중복·채점 ID를 검사한다.

| # | 원본 Markdown | 반영 위치 | 실제 검증 |
|---:|---|---|---|
| 1 | `00-00 ReadMe.md` | 전체 사용 흐름 | `README`, `LAB-ENVIRONMENT`, `tasks/README` |
| 2 | `00-01 Theory.md` | Task 02 Workbench와 Task 04·05 KServe/OpenVINO/vLLM 구조·서빙 | 세 Task의 구조·runtime 안내 |
| 3 | `00-Getting-Started/01-About.md` | 전체 목표 | 안내 문서 |
| 4 | `00-Getting-Started/02-Exam-Details.md` | 수행 전략 | 안내 문서 |
| 5 | `00-Getting-Started/03-How-To-Use.md` | 문제별 start/grade/finish | CLI 도움말·안내 문서 |
| 6 | `01-02 Installation of RHOAI.md` | Task 01 설치 검증 | 01-1 |
| 7 | `01-0301 UserPermission.md` | Task 01 프로젝트 협업 권한 + Task 02 Workbench storage/resources/Git | 01-4, 01-5, 02-3, 02-4, 02-7 |
| 8 | `01-0302 Usermanagement.md` | Task 01 Dashboard 그룹 제한 | 01-2, 01-8 |
| 9 | `01-OpenShift-Architecture/01-Concepts.md` | Task 01 preflight | 안내·API 점검 |
| 10 | `02-01-workbench-size.md` | Task 02 HardwareProfile·Git | 02-5, 02-7 |
| 11 | `02-03 Workbenchsize.md` | Task 02 자원·HardwareProfile·Git | 02-4, 02-5, 02-7 |
| 12 | `02-06 Data Connections.md` | Task 02 Workbench S3 | 02-8, 02-9 |
| 13 | `02-Projects-and-Applications/01-RHOAI-Introduction.md` | Task 01·02 안내 | 안내 문서 |
| 14 | `02-Projects-and-Applications/02-03 Modify_workbench.md` | Task 02 기존 Workbench 수정 | 02-6, 02-7 |
| 15 | `02-Projects-and-Applications/02-RHOAI-Installation.md` | Task 01 설치 검증/전용 설치 문서 | 01-1 |
| 16 | `02-Projects-and-Applications/03-RHOAI-Verification-and-Usage.md` | Task 01 Dashboard 검증 | 01-1, 01-2 |
| 17 | `03-03 ModifyWorkbench.md` | Task 02 CUDA·ConfigMap·Git | 02-6, 02-7 |
| 18 | `03-User-Permissions/01-Users-Projects-and-Permissions.md` | Task 01 user/admin group | 01-2, 01-8 |
| 19 | `03-User-Permissions/02-User-Management-and-RBAC.md` | Task 01 project RBAC | 01-3, 01-4, 01-5 |
| 20 | `03-User-Permissions/03-Resource-Management.md` | Task 02 culling·자원 profile | 02-2, 02-4, 02-5 |
| 21 | `05 S3 configuration.md/02 Creation of Bucket & dataconnection S3.md` | Task 02 S3 connection | 02-8, 02-9 |
| 22 | `05-00 Create a Custom Notebook Image.md` | Task 02 build/import | 02-1, 02-2 |
| 23 | `05-03 CustomImage.md` | Task 02 package·workbench·artifact | 02-1, 02-2, 02-10 |
| 24 | `06 Model.md/02-00 Model Serving API.md` | Task 04 route·token API | 04-2, 04-4, 04-8, 04-9 |
| 25 | `06 Model.md/02-03 Multimode serving.md` | Task 04 serving mode | 04-1, 04-2, 04-8, 04-9 |
| 26 | `06-01 Collaboration with Jupyter Notebooks.md` | Task 02 Git 협업 | 02-7 |
| 27 | `06-03 Add S3.md` | Task 02 Git·S3·model artifact | 02-7~02-10 |
| 28 | `07 Pipeline/07-01 Creating Pipelines with the KubeFlow.md` | Task 03 KFP·5분 schedule | 03-3, 03-7 |
| 29 | `07 Pipeline/07-02 Create Pipeline by Elyra.md` | Task 03 DSPA·Elyra | 03-1, 03-8, 03-9 |
| 30 | `07 Pipeline/07-03 Create pipeline with Elyra.md` | Task 03 3-node Elyra | 03-8, 03-9 |
| 31 | `07-03 Modal.md` | Task 04 public multi-model 대응 | 04-1, 04-2, 04-8, 04-9 |
| 32 | `08-03 Creating Pipelines with the KubeFlow.md` | Task 03 중복 KFP 실습도 동일 계약으로 추적 | 03-3, 03-7 |
| 33 | `09-01 Create Pipeline by Elyra.md` | Task 03 중복 Elyra 개요도 추적 | 03-1, 03-8, 03-9 |
| 34 | `09-03 Create pipeline with Elyra.md` | Task 03 중복 전체 Elyra 실습도 추적 | 03-8, 03-9 |

## 버전 대응 규칙

- V2.13의 notebook size selector는 RHOAI 3.3 `HardwareProfile`로 검증한다.
- V2.13의 ModelMesh Multi-model은 RHOAI 3.3에서 제거됐으므로 다시 설치하지 않는다. 동일한 외부 Route, token/no-token, ONNX/OpenVINO API 행동을 지원되는 KServe `RawDeployment`로 검증한다.
- 원본의 `RHOAI2.13` Git branch는 현재 과정 입력인 `RHOAI3.3`으로 바꾼다. branch/commit/merge 학습 행동은 그대로다.
- 실제 HTPasswd 사용자 생성은 공유 클러스터 인증을 파괴할 수 있으므로 Group/RBAC subject로 제공한다. 권한·멤버십·Dashboard allowlist 결과는 실제 리소스로 채점한다.
- 설치 실습은 공유 클러스터에서 현재 Operator/DSC 검증으로 수행한다. 새 전용 클러스터의 설치 절차는 Task 01의 별도 문서에 보존한다.

