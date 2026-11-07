# Task 11 — Pipeline Server와 모델 Pipeline

원문 `09-01 Create Pipeline by Elyra.md`의 Pipeline Server, 데이터 처리·학습·저장 단계, `carido-model.joblib`, `saved-models` 목표를 유지하고 실행 환경만 AI267 3.3 `dspa-intro`와 KFP v2 artifact 방식으로 바꿨다. `ai267 11`이 `lab start dspa-intro`를 실행하고 전용 Connection과 합성 데이터 pipeline 입력을 준비한다.

## 제공 환경

- 프로젝트: `dspa-intro`
- S3 Connection: `my-s3-connection`
- Bucket: `saved-models` — `ai267 start 11`이 답안 객체 없이 미리 생성하고 접근 가능 여부까지 확인한다. 정리 안전성을 위한 숨은 ownership object는 채점 대상이 아니다.
- Pipeline source: `/tmp/ai267-task11/carido_pipeline.py`
- 단계: `generate-data` → `preprocess-data` → `train-model` → `save-model`

## 요구 사항

1. 프로젝트 `dspa-intro`의 **Pipelines** 탭에서 제공된 connection `my-s3-connection`을 사용해 Pipeline Server를 구성한다.
2. DSPA가 `Ready`가 되고 API server, persistence agent, scheduler Pod가 준비될 때까지 기다린다.
3. 워크스테이션에서 KFP 2.15.2 환경을 만들고 `/tmp/ai267-task11/carido_pipeline.py`를 편집한다. 파일에는 가상 데이터 생성·전처리·학습·S3 저장 component 구현만 제공되며 graph와 compile entry point는 비어 있다.
4. 다음 요구를 만족하도록 pipeline graph와 compile entry point를 직접 작성한다.
   - `@dsl.pipeline` 이름: `carido-training-pipeline`
   - 연결 순서: `generate-data` → `preprocess-data` → `train-model` → `save-model`
   - compile 출력: `/tmp/ai267-task11/carido-training-pipeline.yaml`

완성한 뒤 compile한다.

```bash
cd /tmp/ai267-task11
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install kfp==2.15.2
python carido_pipeline.py
```

5. 생성된 `carido-training-pipeline.yaml`을 Pipeline definition `carido-training-pipeline`으로 import한다.
6. run `carido-training-r1`을 실행해 성공시킨다.
7. run graph에 데이터 생성, 전처리, 학습, 저장의 네 단계가 모두 성공했는지 확인한다.
8. `save-model` 단계가 `saved-models` bucket의 root에 정확히 `carido-model.joblib` 객체를 만들었고 크기가 0보다 큰지 확인한다.

제공된 `save-model` component는 원문 검증 경로인 `s3://saved-models/carido-model.joblib`에 모델을 게시한다. start는 완성된 graph나 YAML을 만들지 않는다. 옛 `manage-resources`, `RHOAI2.13`, `projects-data-nb.ipynb`는 환경 경로이므로 3.3 `dspa-intro`와 합성 component fixture로 교체했다.

완료 후 다음을 실행한다.

```bash
ai267 grade 11
ai267 finish 11
```
