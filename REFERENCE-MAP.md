# AI267 3.3 참고 자료

기준 문서는 로컬 AI267 3.3 EPUB Edition 2(2026-07-02)다.

- `intro.xhtml`: `intro-projects`
- `workbenches.xhtml`: `workbench-creating`, `workbench-connections`, `workbench-working`, `workbench-custom`
- `servingruntimes.xhtml`: `serving-openvino`
- `dspa.xhtml`: `dspa-intro`, `dspa-elyra`, `dspa-kubeflow`

공개 예제 코드는 <https://github.com/RedHatTraining/AI26X-apps>의 `RHOAI3.3` branch와 공식 Lab이 제공하는 `~/course/labs` 파일을 사용한다.

원문에서 결과로 요구한 식별자는 유지한다. Task 01은 `my-lab-pro`/`myworkbench-wb`, Task 04는 `projects-data`/`projects-data-bucket`/`projects-data-connection`/`projects-data-wb`, Task 08은 `my-s3-connection`/`saved-models`/`carido-model.joblib`, Task 09는 `tiger`/`rhoaiserving-using`/`diabetes`, Task 10은 `tas1-devops-wala`/`tas1-devops-wala-s1`/5분, Task 11은 `my-s3-connection`/`saved-models`/`carido-model.joblib`, Task 12는 `pipelines-elyra-wb`/`forecast-pipeline-runtime`/`issues_prediction`을 사용한다.

구형 Lab이 제공하던 환경 식별자는 공식 3.3 Lab 계약으로 바꾼다. Task 05와 Task 07은 `workbench-working/model-training`, Task 08은 `workbench-connections/workbench-connections-wb`, Task 10은 `dspa-kubeflow`, Task 11은 `dspa-intro`와 KFP v2 synthetic starter를 사용한다. 저장소 baseline branch와 starter 경로도 `RHOAI3.3` branch의 실제 구조로 바꾼다. Task 07의 사용자 feature branch 이름과 새 Notebook 경로는 원문처럼 자유다. 이 변경은 `SOURCE-MAP.md`에 구형 값과 새 값을 함께 기록한다.

안전과 자료 충돌을 처리하는 예외는 다음과 같다.

- 설치 문서는 이미 구성된 course cluster의 Operator·DSC를 다시 변경하지 않도록 비채점 사전조건으로 둔다.
- Task 01은 서로 충돌하는 admin/suraj 지시 중 개요의 admin 작업 흐름을 따르고, OAuth identity를 만들지 않은 채 `suraj` Contributor RBAC을 평가한다.
- Task 03은 cluster 전체 설정 대신 task namespace의 `HardwareProfile`로 동일한 선택지 변경을 연습한다.
- custom image 풀이 끝의 문맥과 무관한 joblib 복사 문단은 Task 06 범위에서 제외하고 Task 08의 model 저장 문제에서 다룬다.
- Task 09는 OpenVINO version directory에 합성 ONNX model을 제공하므로 artifact 이름과 입력 shape가 원문 예제와 다르다. project·Connection·deployment·storage parent path와 무인증 external route 목표는 유지한다.
- Task 12는 `forecast-pipeline-runtime` display name을 유지하고 3.3 공식 `registry.lab.example.com:8443/redhattraining/dspa-elyra-runtime:v2.0` image를 연결한다. 이 image는 RHOAI 3.3 Dashboard step log 확인에 필요한 2025.2+ runtime 계약을 따른다.

## 핵심 API

| 목적 | RHOAI 3.3 API |
| --- | --- |
| Workbench | `kubeflow.org/v1`, `Notebook` |
| Workbench resources | `infrastructure.opendatahub.io/v1`, `HardwareProfile` |
| Dashboard access | `services.platform.opendatahub.io/v1alpha1`, `Auth` |
| Pipeline server | `datasciencepipelinesapplications.opendatahub.io/v1`, `DataSciencePipelinesApplication` |
| Kubernetes pipeline store | `pipelines.kubeflow.org/v2beta1`, `Pipeline`/`PipelineVersion` |
| Predictive serving | `serving.kserve.io/v1beta1`, `InferenceService` |

이 저장소는 공개 학습 자료를 현재 버전에 맞게 재구성한 비공식 연습 환경이다. 실제 시험 유출 문제나 Red Hat 공식 채점 스크립트가 아니다.
