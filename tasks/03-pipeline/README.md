# Task 03 · KFP·Elyra Pipeline·예약 실행

기존 fraud training KFP v2 문제를 유지하고, 번호형 실습의 `tas1-devops-wala` 5분 schedule과 RHOAI 3.3 교재의 Elyra 3-node pipeline을 같은 환경에 추가한다.

`ai267 start 03`은 전용 MinIO, 합성 transaction/support-case 데이터, DSPA DB Secret, KFP Python source, Elyra용 세 Python node와 빈 pipeline 파일을 자동 준비한다. DSPA 설정·컴파일·import·run·schedule·Elyra 편집은 응시자가 수행한다.

## 수행 목표

1. `aws-connection-fraud-s3`를 `exam-provided-minio` 값으로 완성하고 `resources/dspa-starter.yaml`의 TODO를 수정해 `dspa/dspa`를 Ready로 만든다.
2. Python 3.11+와 `kfp>=2.14.3`으로 제공 `fraud_pipeline.py`를 컴파일한다. `validate`, `train`, `evaluate`가 독립 component여야 한다. compiled IR YAML을 `fraud-training-pipeline`에 저장하고 `ex267.io/kfp-sdk`에 실제 버전을 쓴다.
3. `pipeline-runner`, S3 Secret, component request/limit, cache/retry, run별 artifact prefix를 검증해 `pipeline-evidence`에 기록한다.
4. 서로 다른 `max_depth` 값으로 두 run을 성공시킨다. 생성 Workflow에 `ex267.io/max-depth` 라벨을 붙이고 승인 model URI/SHA-256을 기록한다.
5. compiled pipeline을 `tas1-devops-wala` 이름으로 import한다. `tas1-devops-wala-s1` schedule을 **Periodic / every 5 minutes**로 만들고 적어도 한 scheduled run을 성공시킨다. schedule이 만든 Workflow에는 `ex267.io/scheduled-run=true` 라벨을 붙이고 `schedule-evidence`를 갱신한다.
6. `resources/elyra-workbench-starter.yaml`을 설치 환경의 **Standard Data Science** image로 완성해 `pipelines-elyra-wb`와 10Gi PVC를 만든다. Elyra는 Standard Data Science 계열에서만 지원되므로 Minimal/CUDA image를 쓰지 않는다.
7. JupyterLab에서 `RHOAI3.3` 기준 입력 파일을 사용한다. `issues_prediction.pipeline`에 다음 세 node를 순서대로 연결한다.

   - `data_ingestion.py` → output `data.csv`
   - `data_preprocessing.py` → output `clean-data.csv`
   - `data_training_and_forecasting.py` → output `forecast-data.csv`

8. 모든 Elyra node가 제공된 `forecast-pipeline-runtime` image를 사용하게 하고 Kubernetes Secret mapping으로 `aws-connection-fraud-s3`의 네 AWS key를 주입한다. pipeline을 저장·submit해 성공시킨다.
9. 성공한 Elyra Workflow 이름, Git 40자리 commit SHA, 세 output object의 서로 다른 SHA-256을 `elyra-evidence`에 기록한다.

## Console 위치

- Pipeline server: RHOAI **Projects → ex267-t03-pipeline → Pipelines → Configure pipeline server**
- Import/schedule: RHOAI **Pipelines → Pipelines → Import pipeline**, pipeline의 **Actions → Create schedule**
- Run 확인: RHOAI **Pipelines → Experiments and runs → Runs**
- Elyra: RHOAI **Projects → ex267-t03-pipeline → Workbenches → pipelines-elyra-wb → Open** 후 JupyterLab Launcher의 **Pipeline Editor**
- Elyra runtime image: JupyterLab 왼쪽 **Runtime Images**, pipeline editor 오른쪽 **Open Panel → Generic Node Defaults**
- Secret mapping: pipeline 설정 **Kubernetes Secrets**에서 AWS env 이름과 같은 Secret key 연결
- S3 결과: MinIO console 또는 새 Workbench process에서 `issues_prediction-<timestamp>/` 아래 세 CSV 확인

```bash
ai267 grade 03
ai267 finish 03
```

