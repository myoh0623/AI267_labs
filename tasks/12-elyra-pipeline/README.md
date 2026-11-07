# Task 12 — Elyra Pipeline

원문 `09-03 Create pipeline with Elyra.md`의 Workbench 생성, Runtime Image, 네 개의 Secret mapping, 3-node graph, 실행·검증 목표를 유지한다. 저장소 branch와 실습 경로, 프로젝트·bucket 이름만 공식 AI267 3.3 `dspa-elyra` Lab에 맞췄다.

`ai267 12`는 공식 Lab을 시작해 다음 **기반 환경만** 제공한다.

- 프로젝트와 Data Science Pipeline Server: `dspa-elyra`
- 기존 S3 Connection: `s3-minio`
- bucket과 입력 데이터: `dspa-elyra-bucket/data/data.zip`
- 원문 Secret 이름을 사용할 수 있게 하는 compatibility Secret: `aws-connection-s3-minio`

공식 Lab이 별도의 예제 Workbench를 표시하더라도 이 문제에는 사용하지 않는다. 아래 Workbench, Runtime Image, pipeline graph는 학습자가 직접 만든다.

## 요구 사항

1. 프로젝트 `dspa-elyra`에 Workbench를 새로 만든다.
   - Name: `pipelines-elyra-wb`
   - Image: `Jupyter | Data Science | CPU | Python 3.12` — 원문의 **Standard Data Science**에 해당하는 3.3 이미지
   - 새 persistent storage: `10 GiB`
   - Existing Connection: `s3-minio`
2. Workbench를 시작하고 JupyterLab에서 다음 저장소를 복제한다.
   - URL: `https://github.com/RedHatTraining/AI26X-apps.git`
   - Branch: `RHOAI3.3`
   - 작업 경로: `AI26X-apps/dspa/elyra`
3. JupyterLab의 **Runtime Images**에서 다음 custom runtime image를 추가한다.
   - Display name: `forecast-pipeline-runtime`
   - Image name: `registry.lab.example.com:8443/redhattraining/dspa-elyra-runtime:v2.0`
4. `AI26X-apps/dspa/elyra/issues_prediction.pipeline`을 Elyra Pipeline Editor로 연다. **Pipeline Properties → Generic Node Defaults**에서 다음을 설정한다.
   - Runtime image: `forecast-pipeline-runtime`
   - Kubernetes Secrets:

| Environment Variable | Secret Name | Secret Key |
| --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | `aws-connection-s3-minio` | `AWS_ACCESS_KEY_ID` |
| `AWS_SECRET_ACCESS_KEY` | `aws-connection-s3-minio` | `AWS_SECRET_ACCESS_KEY` |
| `AWS_S3_ENDPOINT` | `aws-connection-s3-minio` | `AWS_S3_ENDPOINT` |
| `AWS_S3_BUCKET` | `aws-connection-s3-minio` | `AWS_S3_BUCKET` |

5. 다음 세 Python 파일을 canvas에 추가하고 정확한 순서로 연결한다.

```text
data_ingestion.py -> data_preprocessing.py -> data_training_and_forecasting.py
```

6. 각 node의 **Open Properties → Outputs**에 다음 값을 설정한다.

| Node | Output file |
| --- | --- |
| `data_ingestion.py` | `data.csv` |
| `data_preprocessing.py` | `clean-data.csv` |
| `data_training_and_forecasting.py` | `forecast-data.csv` |

7. pipeline을 저장하고 **Run Pipeline**을 눌러 run 이름을 `issues_prediction`으로 실행한다. 모든 node가 성공할 때까지 기다린다. **Experiments and runs → Run details**에서 세 Task를 각각 열어 Log가 표시되고 오류 없이 끝났는지 확인한다. RHOAI 3.3에서는 Task Log를 MinIO 객체가 아니라 Dashboard의 Log 화면에서 확인한다. 이를 위해 원문의 display name은 유지하되 backing image는 3.3 공식 Lab의 2025.2+ 호환 runtime을 사용한다.
8. MinIO의 `dspa-elyra-bucket/issues_prediction-<timestamp>/` 한 폴더 안에 `data.csv`, `clean-data.csv`, `forecast-data.csv`가 모두 생성됐는지 확인한다.

## Console 위치

- Workbench: **Projects → dspa-elyra → Workbenches → Create workbench**
- Runtime Image: **JupyterLab → Runtime Images → +**
- Pipeline 설정: **Pipeline Editor → Open Panel → Pipeline Properties → Generic Node Defaults**
- 실행 결과: **Data Science Pipelines → Experiments and runs**
- MinIO: `https://minio-ui-minio.apps.lab.example.com` (`minio` / `minio123`)

완료 후 다음을 실행한다.

```bash
ai267 grade 12
ai267 finish 12
```

`finish/reset`은 공식 `dspa-elyra` Lab과 Task 12가 만든 compatibility fixture를 정리한다.
