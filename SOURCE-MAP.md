# 첨부 Markdown 17개 대응표

첨부 문서 안의 명령은 작업 지시가 아니라 문제 원문으로만 사용했다. 첫 안내·이론 문서와 설치 문서는 채점 전 안내로, 나머지 실습 문서는 입력 순서를 유지한 Task로 대응한다.

| 순서 | 첨부 파일 | 유형 | 재구성 위치 |
| ---: | --- | --- | --- |
| 1 | `00-00 ReadMe.md` | 안내 | `README.md` |
| 2 | `00-01 Theory.md` | 이론 | `docs/THEORY.md` |
| 3 | `01-02 Installation of RHOAI.md` | 사전조건 | `docs/SETUP.md` |
| 4 | `01-0301 UserPermission.md` | 실습 | Task 01 |
| 5 | `01-0302 Usermanagement.md` | 실습 | Task 02 |
| 6 | `02-01-workbench-size.md` | 실습 | Task 03 |
| 7 | `02-03 Workbenchsize.md` | 보완 실습 | Task 03 |
| 8 | `02-06 Data Connections.md` | 실습 | Task 04 |
| 9 | `03-03 ModifyWorkbench.md` | 실습 | Task 05 |
| 10 | `05-00 Create a Custom Notebook Image.md` | 실습 | Task 06 |
| 11 | `05-03 CustomImage.md` | 보완 실습 | Task 06 |
| 12 | `06-01 Collaboration with Jupyter Notebooks.md` | 실습 | Task 07 |
| 13 | `06-03 Add S3.md` | 실습 | Task 08 |
| 14 | `07-03 Modal.md` | 실습 | Task 09 |
| 15 | `08-03 Creating Pipelines with the KubeFlow.md` | 실습 | Task 10 |
| 16 | `09-01 Create Pipeline by Elyra.md` | 실습 | Task 11 |
| 17 | `09-03 Create pipeline with Elyra.md` | 실습 | Task 12 |

## 설치 문서를 채점하지 않는 이유

설치 문서의 `rhoai-install`은 AI263 2.x 환경의 Operator 설치 Lab이며 AI267 3.3 EPUB에 같은 이름의 공식 Lab이 없다. 이 저장소의 문제는 RHOAI 3.3 Operator와 `DataScienceCluster`가 이미 준비된 course cluster에서 실행한다. 기존 cluster에서 Operator·DSC·OAuth 또는 Serverless 구성을 다시 설치하는 것은 다른 실습과 사용자의 전역 환경을 손상시킬 수 있으므로, 설치 내용은 `docs/SETUP.md`의 사전조건과 읽기 전용 확인으로만 변환하고 점수를 부여하지 않는다.

## 원문 충돌과 안전한 동등 실습

- Task 01 원문의 개요는 `admin`이 Workbench를 만든다고 하지만 풀이와 예상 출력은 `suraj` 로그인을 지시한다. fixture는 cluster 인증을 바꾸지 않기 위해 OAuth identity나 암호를 만들지 않는다. 따라서 현재 `admin` 세션에서 리소스를 만들고, `suraj`의 Contributor RBAC을 실제 RoleBinding으로 평가한다.
- Task 03 원문은 cluster 전체 `notebookSizes`를 바꾼다. RHOAI 3.3에서는 해당 설정 대신 namespaced `HardwareProfile`을 사용한다. 다른 사용자와 문제에 영향을 주지 않도록 `workbench-creating`에만 `Large`와 `X Large` 연습 profile을 제공하고, 그 project 안에서 숨김·새 profile 선택을 평가한다. 이는 cluster 전체 설정 변경이 아니라 project-scoped simulation이다.
- 두 번째 custom image 문서의 풀이 끝에는 custom image 목표와 무관한 `carido-model.joblib` 저장 문단이 복사되어 있다. 이 문단은 Task 06에서 제외하고, model 저장 요구는 해당 S3 실습을 재구성한 Task 08에서 평가한다.

## 공식 3.3 Lab에 맞춘 환경 식별자

다음 값은 문제의 결과 식별자가 아니라 구형 Lab이 제공하던 namespace·Workbench·starter 경로이므로 공식 3.3 환경으로 교체했다.

| Task | 2.x 제공 환경 | AI267 3.3 제공 환경 |
| --- | --- | --- |
| 05 | `notebooks-collaboration` / `git-experiments` | `workbench-working` / `model-training` |
| 07 | `notebooks-collaboration` / `git-experiments` | `workbench-working` / `model-training` |
| 08 | `serving-saving` / `serving-saving-wb` / `intro/projects-data/projects-data-nb.ipynb` | `workbench-connections` / `workbench-connections-wb` / `workbench/connections/workbench-connections.ipynb` |
| 10 | `pipelines-kfp`, Python 3.9, KFP 2.14 계열 | `dspa-kubeflow`, Python 3.13, KFP 2.15.2 |
| 11 | `manage-resources` / `manage-resources-wb` / 구형 Notebook | `dspa-intro` / standalone KFP v2 synthetic component starter |

Task 09는 원문의 `tiger`, `rhoaiserving-using`, `diabetes`, `models/diabetes`, external route와 인증 비활성 요구를 유지한다. 다만 가상 model 사용을 허용한 요청에 따라 입력 artifact는 OpenVINO 3.3이 요구하는 version directory의 `models/diabetes/1/model.onnx`으로 제공하고, 합성 model의 입력 shape는 5이다. Task 12는 원문의 runtime display name `forecast-pipeline-runtime`을 유지하되 backing image는 3.3 공식 Lab의 `registry.lab.example.com:8443/redhattraining/dspa-elyra-runtime:v2.0`을 사용한다.

## 의도적으로 제거한 2.x 요소

- `lab start -t AI262|AI263|AI265|AI266 ...`
- `.ocp4.example.com` 고정 주소
- `RHOAI2.13`, Python 3.9, `intro/notebooks-collaboration`
- `OdhDashboardConfig.spec.notebookSizes`
- 존재 여부가 불명확한 `rhods-user`/`rhods-admin` ClusterRole
- ModelMesh Multi-model server와 `multimodel-server`

관련 문서를 한 Task로 묶을 때도 위에서 명시한 복사 잔재를 제외한 문제의 고유 요구를 유지했다. 예를 들어 Task 06은 두 package의 실제 설치와 description/software/package metadata를 모두 평가한다. 결과로 요구된 이름은 유지하고, 공식 Lab이 제공하는 namespace·Workbench·starter 경로, 3.3에서 존재하지 않는 API·runtime과 Lab 명령만 위 대응에 따라 교체했다.

Task 07 원문은 새 Notebook 추적과 feature branch 생성·병합만 요구하며 branch나 Notebook 이름을 지정하지 않는다. 따라서 feature branch 이름과 새 `.ipynb` 경로는 자유이고, 채점은 특정 이름 대신 원격 `RHOAI3.3` 이후의 Git 이력과 병합 관계를 사용한다.
