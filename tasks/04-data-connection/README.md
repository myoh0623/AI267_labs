# Task 04 — S3 Connection과 객체 검증

원문 `02-06 Data Connections.md`의 프로젝트·bucket·connection·Workbench 이름과 생성 과정을 유지하고, endpoint와 이미지 표시만 RHOAI 3.3 환경에 맞췄다. `ai267 04`는 공식 `lab start workbench-connections`로 MinIO를 시작하고 빈 프로젝트 `projects-data`만 준비한다. 아래 bucket, Connection, Workbench는 학습자가 직접 만든다.

## 요구 사항

1. MinIO UI에서 bucket `projects-data-bucket`을 만든다.
2. 프로젝트 `projects-data`의 **Connections**에서 `S3 compatible object storage - v1` Connection `projects-data-connection`을 만든다.

| 필드 | 값 |
| --- | --- |
| Access key | `minio` |
| Secret key | `minio123` |
| Endpoint | `https://minio-api-minio.apps.lab.example.com` |
| Region | `us-east-1` |
| Bucket | `projects-data-bucket` |

3. 같은 프로젝트에 Workbench `projects-data-wb`를 새로 만든다.
   - Image: `Jupyter | Data Science | CPU | Python 3.12` — 원문의 **Standard Data Science**에 해당하는 3.3 이미지
   - Connection: 기존 `projects-data-connection`
4. Workbench가 Running이 되면 JupyterLab에서 `https://github.com/RedHatTraining/AI26X-apps.git`을 복제하고 `RHOAI3.3` 브랜치를 checkout한다.
5. `AI26X-apps/workbench/connections/workbench-connections.ipynb`를 열고 주어진 S3 환경 변수로 upload와 download를 모두 수행한다.
6. `workbench/connections/dataset.csv`를 bucket root의 key `dataset.csv`로 업로드하고, 다시 `workbench/connections/downloaded-dataset.csv`로 다운로드한다. 두 로컬 파일의 내용이 같은지 확인한다.

```python
from pathlib import Path

s3.upload_file("dataset.csv", bucket_name, "dataset.csv")
s3.download_file(bucket_name, "dataset.csv", "downloaded-dataset.csv")
assert Path("dataset.csv").read_bytes() == Path("downloaded-dataset.csv").read_bytes()
```

MinIO UI는 `https://minio-ui-minio.apps.lab.example.com`이다. start는 `projects-data-bucket`, Connection, Workbench를 미리 만들지 않는다.

## Console 위치

- Connection: **Projects → projects-data → Connections**
- Workbench: **Projects → projects-data → Workbenches → Create workbench**

완료 후 다음을 실행한다.

```bash
ai267 grade 04
ai267 finish 04
```

`finish/reset`은 `projects-data` 프로젝트와 이 문제에서 만든 `projects-data-bucket`을 정리한다.
