# AI267 v3.3 참고 리소스 매핑

| EX267 문제 | 참고한 AI267 v3.3 리소스 |
| --- | --- |
| 01 | `chapter-01-projects`, 플랫폼 설치/DSC 확인, Dashboard `Auth`, Project·RoleBinding·S3 connection 형식 |
| 02 | `chapter-02-workbench`의 Notebook·PVC·ImageStream·BuildConfig, HardwareProfile, custom image, Git, S3 형식 |
| 03 | `chapter-06-pipelines`, `chapter-07-pipeline-operations`, RHOAI 3.3 Elyra guided exercise와 공개 `RedHatTraining/AI26X-apps`의 DSPA·KFP·artifact/experiment 형식 |
| 04 | `chapter-03-model-serving`, `chapter-04-model-storage`, RHOAI 3.3 custom runtime/OpenVINO guided exercise의 ServingRuntime·InferenceService·V2·token 형식 |
| 05 | Chapter 3/4 serving 리소스와 AI267 3.3 GPU·vLLM 학습 자료 |
| 06 | AI267 3.3 `serving-modelregistry` Lab의 MariaDB·ONNX v1/v2·OCI ModelCar와 v1beta1 API 계약 |
| 07 | `chapter-05-trustyai`의 TrustyAIService·capture·monitoring 형식 |
| 08 | `chapter-08-optimization-evaluation`의 quantization Job·LMEvalJob 형식 |
| 09 | `chapter-09-genai-patterns`의 mock LLM·RAG·tool·guardrail 애플리케이션 |
| 10 | Chapter 2/6/7/8/9의 digest·run·artifact·rollback 증적을 통합 |

이 연습 환경은 공개 학습 자료 기반의 비공식 모의 과제이며, 실제 시험에서 유출된 리소스나 공식 채점 스크립트가 아니다.

AI26X 참고 기준은 <https://github.com/RedHatTraining/AI26X-apps>의 `main` commit `3ac8cb012785f19060457c91c9ef56ee963fc0fe`이다. 해당 저장소의 Python 3.9 예제를 그대로 복제하지 않고, Task 03의 합성 데이터와 RHOAI 3.3 Python 3.12/KFP v2 계약에 맞게 다시 작성했다.

추가 비교 기준은 <https://github.com/anishrana2001/Openshift/tree/40d6458045d7134c9aa1f15d749325faa3bc6062/EX267-V2.13>이다. 해당 commit의 Markdown 34개를 모두 열거한 대응표는 [V213-COVERAGE.md](V213-COVERAGE.md)와 [source-coverage.yaml](source-coverage.yaml)에 있다. 원문 해설을 복제하지 않고 각 실습 행동을 현재 10개 문제와 RHOAI 3.3 리소스에 재구성했다.

