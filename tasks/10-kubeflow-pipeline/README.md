# Task 10 — Kubeflow SDK Pipeline

원문 `08-03 Creating Pipelines with the KubeFlow.md`의 pipeline 이름, 5분 schedule, 성공 run 요구를 유지하고 실행 환경만 AI267 3.3 `dspa-kubeflow`와 KFP 2.15.2로 갱신했다. `ai267 10`이 `lab start dspa-kubeflow`를 실행하고 원문의 starter를 `/tmp/simple_pipeline.py`에 준비한다.

## 요구 사항

1. 워크스테이션에서 `/tmp`로 이동한다.
2. Python 3.13 가상환경과 KFP SDK 2.15.2를 준비한다.

```bash
cd /tmp
uv venv --allow-existing --python 3.13 /tmp/ai267-task10-venv
source /tmp/ai267-task10-venv/bin/activate
uv pip install kfp==2.15.2
python /tmp/simple_pipeline.py
```

3. 생성된 `/tmp/simple_rhoai_pipeline.yaml`을 프로젝트 `dspa-kubeflow`에 Pipeline definition `tas1-devops-wala`로 import한다.
4. Schedule `tas1-devops-wala-s1`을 만든다.
   - Experiment: `Default`
   - Trigger type: `Periodic`
   - Run every: `5 minutes`
   - Pipeline: `tas1-devops-wala`
5. schedule이 활성화되어 있는지 확인하고 최소 한 번의 scheduled run이 자동으로 시작될 때까지 기다린다.
6. 해당 run이 `Succeeded`인지 확인한다.

3.3 EPUB의 sentiment threshold 실패·수정과 Kubernetes-native `Pipeline`/`PipelineVersion` 전환은 별도 Guided Exercise 확장 내용이다. 원문 schedule 문제를 바꾸지 않기 위해 이 Task에서는 요구하지 않는다.

완료 후 다음을 실행한다.

```bash
ai267 grade 10
ai267 finish 10
```
