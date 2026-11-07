# AI267 3.3 공식 Lab 연결

모든 문제는 하나의 공식 Lab을 독립적으로 실행한다. 다음 문제를 시작하기 전에 현재 문제를 `finish` 또는 `reset`해야 한다.

| Task | 시작 | 종료 | 공식 Lab baseline project | 문제 풀이 target |
| --- | --- | --- | --- | --- |
| 01 | `lab start workbench-creating` | `cd && lab finish workbench-creating` | `workbench-creating` | `my-lab-pro` (학습자 생성) |
| 02 | `lab start intro-projects` | `cd && lab finish intro-projects` | `intro-projects` | cluster-scoped `Auth/auth`와 `Group` |
| 03 | `lab start workbench-creating` | `cd && lab finish workbench-creating` | `workbench-creating` | `workbench-creating` |
| 04 | `lab start workbench-connections` | `cd && lab finish workbench-connections` | `workbench-connections` | `projects-data` (custom base project) |
| 05 | `lab start workbench-working` | `cd && lab finish workbench-working` | `workbench-working` | `workbench-working` |
| 06 | `lab start workbench-custom` | `cd && lab finish workbench-custom` | `workbench-custom` | `workbench-custom` |
| 07 | `lab start workbench-working` | `cd && lab finish workbench-working` | `workbench-working` | `workbench-working` |
| 08 | `lab start workbench-connections` | `cd && lab finish workbench-connections` | `workbench-connections` | `workbench-connections` |
| 09 | `lab start serving-openvino` | `cd && lab finish serving-openvino` | `serving-openvino` | `tiger` (학습자 생성) |
| 10 | `lab start dspa-kubeflow` | `cd && lab finish dspa-kubeflow` | `dspa-kubeflow` | `dspa-kubeflow` |
| 11 | `lab start dspa-intro` | `cd && lab finish dspa-intro` | `dspa-intro` | `dspa-intro` |
| 12 | `lab start dspa-elyra` | `cd && lab finish dspa-elyra` | `dspa-elyra` | `dspa-elyra` |

## wrapper 동작

`ai267 NN`은 다음 순서로 동작한다.

1. 다른 Task state와 위 공식 Lab들의 `Started` 상태를 확인한다.
2. 정확한 `lab start`를 실행한다.
3. 해당 문제에만 필요한 안전한 fixture를 준비한다.
4. 문제 README를 터미널에 표시한다.

`ai267 finish NN`은 custom grader가 100점일 때만 공식 `lab finish`를 호출한다. Task 02의 전역 설정 복구 hook은 성공·reset 모두에서 실행된다.

## 공식 Lab과 custom fixture

- Task 01은 RBAC 참조용 User 객체와 전역 2 CPU/8 GiB profile만 보충한다. `my-lab-pro`, RoleBinding, Workbench는 학습자가 직접 만든다.
- Task 02는 EPUB에 동일한 user-management GE가 없어 `intro-projects`를 기반으로 누락된 User 객체만 보충한다. `Auth`, 전체 Group 목록, ClusterRoleBinding을 검증된 JSON으로 원자적 백업하며 전역 접근 설정은 start가 변경하지 않는다.
- Task 03은 제거 대상 `Large`, `X Large` profile만 보충한다.
- Task 04는 공식 Lab의 MinIO만 사용하고 빈 `projects-data` 프로젝트를 보충한다. `projects-data-bucket`, `projects-data-connection`, `projects-data-wb`는 학습자가 직접 만든다.
- Task 05·07은 공식 Lab의 프로젝트, 기존 Workbench와 자료를 사용한다. Task 06은 공식 프로젝트와 build 자료만 사용하며 custom image와 `custom-wb`는 학습자가 만든다.
- Task 08은 답안 객체 `carido-model.joblib`이 없는 `saved-models` bucket과 합성 학습 코드 `train_carido_model.py`를 준비하고 Workbench PVC에도 복사한다. Connection과 모델 결과는 만들지 않는다.
- Task 09는 `models-bucket/models/diabetes/1/model.onnx`에 작은 합성 ONNX 입력만 준비한다. `tiger`, Connection, `InferenceService`는 만들지 않는다.
- Task 10은 `/tmp/simple_pipeline.py` starter와 ownership marker만 든 빈 가상환경 디렉터리를 준비한다. 학습자가 `uv venv --allow-existing`으로 환경을 초기화하며, Pipeline definition, schedule, run은 만들지 않는다.
- Task 11은 답안 객체가 없는 `saved-models` bucket, Dashboard용 `my-s3-connection` 입력, `/tmp/ai267-task11/carido_pipeline.py`의 standalone component 구현을 준비한다. 완성된 graph/YAML, Pipeline Server, definition, run은 만들지 않는다.
- Task 12는 공식 Lab의 `dspa-elyra` project·DSPA·`s3-minio`·bucket 입력만 사용하고, 원문 mapping 이름을 위한 `aws-connection-s3-minio` compatibility Secret만 보충한다. `pipelines-elyra-wb`, custom Runtime Image, pipeline graph와 run은 만들지 않는다.

각 custom fixture는 시작 전 기존 파일·객체를 거부하거나 백업하고, `finish/reset`에서 task가 만든 범위만 삭제하거나 원본을 복원한다. Task 08·09·11이 직접 만든 S3 bucket은 무작위 ownership object가 로컬 token과 정확히 일치할 때만 전체 삭제한다. S3 의존 cleanup은 공식 Lab을 종료하기 전에 수행한다.
