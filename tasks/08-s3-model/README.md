# Task 08 — 학습 모델을 S3에 저장

원문 `06-03 Add S3.md`의 `my-s3-connection`, `saved-models`, `carido-model.joblib` 요구를 유지하고 namespace와 Workbench만 공식 RHOAI 3.3 `workbench-connections` 환경으로 바꿨다. `ai267 08`이 `lab start workbench-connections`을 실행하고 답안 객체 `carido-model.joblib`이 없는 `saved-models` bucket과 합성 학습 입력을 준비한다. 정리 안전성을 위한 숨은 ownership object는 채점 대상이 아니다.

## 요구 사항

1. 다음 값으로 S3 connection `my-s3-connection`을 만들고 `workbench-connections-wb`에 연결한 뒤 Workbench를 다시 시작한다.

| 필드 | 값 |
| --- | --- |
| Access key | `minio` |
| Secret key | `minio123` |
| Endpoint | `https://minio-api-minio.apps.lab.example.com` |
| Region | `us-east-1` |
| Bucket | `saved-models` |

2. JupyterLab에 준비된 `AI26X-apps` 복제본을 사용한다. 없다면 직접 복제하고 원격 `RHOAI3.3`을 기준으로 로컬 `RHOAI3.3`을 만든 뒤 feature branch `experiment2`를 만든다.
3. `AI26X-apps/workbench/connections/workbench-connections.ipynb`를 열고 Notebook에 적힌 S3 환경 변수 확인과 `dataset.csv` 업로드 작업을 수행한다. 이어서 같은 객체를 다시 다운로드하고 원본과 byte 단위로 같은지 확인한다.

```python
from pathlib import Path

s3.download_file(bucket_name, "dataset.csv", "downloaded-dataset.csv")
assert Path("dataset.csv").read_bytes() == Path("downloaded-dataset.csv").read_bytes()
```

4. 같은 Notebook 맨 아래에 `# saving THE JOBLIB Model file`로 시작하는 Cell을 추가한다. 제공된 `/opt/app-root/src/train_carido_model.py`를 실행해 `ml_model`을 준비하고, **같은 Cell 안에서 학습자가 직접** `joblib.dump(...)`를 호출해 저장소 root에 모델을 저장한다. `%run`만 실행하고 저장 코드를 생략하면 완료가 아니다.

Cell에는 적어도 다음 구조가 실제 실행 가능한 코드로 들어 있어야 하며, 실행 결과도 Notebook에 저장한다.

```python
# saving THE JOBLIB Model file
%run /opt/app-root/src/train_carido_model.py
import joblib
joblib.dump(ml_model, "/opt/app-root/src/AI26X-apps/carido-model.joblib")
```

실행 후 생성된 파일이 저장소 root의 정확한 경로에 있고 비어 있지 않은지 확인한다.

```bash
test -s /opt/app-root/src/AI26X-apps/carido-model.joblib
```

5. 생성된 파일 경로는 정확히 다음과 같아야 한다.
   - `AI26X-apps/carido-model.joblib`
6. 모델을 다음 위치에 업로드한다.
   - bucket: `saved-models`
   - key: `carido-model.joblib`

업로드 Cell을 실행하고 실행 결과를 Notebook에 저장한다.

```python
s3.upload_file(
    '/opt/app-root/src/AI26X-apps/carido-model.joblib',
    bucket_name,
    'carido-model.joblib',
)
```

7. S3에서 다음 exact 경로로 다시 다운로드하고 로컬 모델과 byte 단위로 같으며 파일 크기가 0보다 큰지 확인한다. 이 다운로드 Cell도 실행 결과를 저장한다.

```python
from pathlib import Path

s3.download_file(
    bucket_name,
    'carido-model.joblib',
    '/opt/app-root/src/AI26X-apps/downloaded-carido-model.joblib',
)
source_model = Path('/opt/app-root/src/AI26X-apps/carido-model.joblib')
downloaded_model = Path('/opt/app-root/src/AI26X-apps/downloaded-carido-model.joblib')
assert source_model.stat().st_size > 0
assert source_model.read_bytes() == downloaded_model.read_bytes()
```

8. 임시로 다운로드한 dataset과 두 model binary를 로컬 Git exclude에 등록한다. 이 설정은 저장소에 commit되지 않는다.

```bash
printf '/workbench/connections/downloaded-dataset.csv\n/carido-model.joblib\n/downloaded-carido-model.joblib\n' \
  >> /opt/app-root/src/AI26X-apps/.git/info/exclude
```

Notebook의 모든 실행 결과를 저장한 뒤, `workbench/connections/workbench-connections.ipynb`를 `experiment2`에 commit하고 로컬 `RHOAI3.3`에 병합한다. commit하기 전에 출력에서 S3 자격 증명을 지운다. `carido-model.joblib`과 `downloaded-carido-model.joblib` 두 binary 및 S3 자격 증명은 Git에 추가하거나 commit하지 않는다. 마지막에 `git status --short`가 빈 출력인지 확인한다.

`RHOAI2.13`, `host_base`, `AWS_ENDPOINT`는 사용하지 않는다. RHOAI 3.3 연결 변수는 `AWS_S3_ENDPOINT`와 `AWS_S3_BUCKET`이다.

합성 데이터와 모델 학습에 사용할 입력 코드는 Workbench Terminal과 워크스테이션 양쪽에서 확인할 수 있다. 이 파일은 `ml_model`을 준비하는 입력이며, 4번의 `joblib.dump(...)` 호출과 6·7번의 S3 호출은 Notebook Cell에 직접 작성하고 실행한다.

```bash
# Workbench Terminal
sed -n '1,240p' /opt/app-root/src/train_carido_model.py

# workstation
sed -n '1,240p' /tmp/train_carido_model.py
```

완료 후 다음을 실행한다.

```bash
ai267 grade 08
ai267 finish 08
```
