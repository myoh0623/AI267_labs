"""Synthetic four-stage KFP v2 pipeline used by AI267 practice Task 11."""

from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Model, Output


PYTHON_IMAGE = "registry.access.redhat.com/ubi9/python-312:latest"


@dsl.component(base_image=PYTHON_IMAGE)
def generate_data(raw_data: Output[Dataset]) -> None:
    import csv

    with open(raw_data.path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["age", "glucose", "bmi", "risk"])
        for index in range(1, 201):
            age = 20 + index % 55
            glucose = 70 + (index * 7) % 130
            bmi = 18 + (index * 3) % 22
            risk = int(glucose > 135 or (age > 55 and bmi > 30))
            writer.writerow([age, glucose, bmi, risk])


@dsl.component(base_image=PYTHON_IMAGE)
def preprocess_data(raw_data: Input[Dataset], clean_data: Output[Dataset]) -> None:
    import csv

    with open(raw_data.path, encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    with open(clean_data.path, "w", newline="", encoding="utf-8") as destination:
        writer = csv.writer(destination)
        writer.writerow(["age", "glucose", "bmi", "risk"])
        for row in rows:
            writer.writerow(
                [int(row["age"]), int(row["glucose"]), int(row["bmi"]), int(row["risk"])]
            )


@dsl.component(
    base_image=PYTHON_IMAGE,
    packages_to_install=["joblib==1.4.2", "scikit-learn==1.5.2"],
)
def train_model(clean_data: Input[Dataset], model: Output[Model]) -> None:
    import csv

    import joblib
    from sklearn.linear_model import LogisticRegression

    with open(clean_data.path, encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    features = [
        [float(row["age"]), float(row["glucose"]), float(row["bmi"])] for row in rows
    ]
    labels = [int(row["risk"]) for row in rows]
    estimator = LogisticRegression(max_iter=500, random_state=267)
    estimator.fit(features, labels)
    joblib.dump(estimator, model.path)
    model.metadata["framework"] = "scikit-learn"


@dsl.component(base_image=PYTHON_IMAGE)
def save_model(
    model: Input[Model],
    published_model: Output[Model],
    s3_endpoint: str = "https://minio-api-minio.apps.lab.example.com",
    s3_bucket: str = "saved-models",
    s3_key: str = "carido-model.joblib",
    s3_access_key: str = "minio",
    s3_secret_key: str = "minio123",
    s3_region: str = "us-east-1",
) -> None:
    import datetime
    import hashlib
    import hmac
    import shutil
    import ssl
    import urllib.parse
    import urllib.request

    shutil.copyfile(model.path, published_model.path)

    with open(model.path, "rb") as stream:
        payload = stream.read()
    parsed = urllib.parse.urlsplit(s3_endpoint.rstrip("/"))
    canonical_uri = urllib.parse.quote(
        f"/{s3_bucket}/{s3_key.lstrip('/')}", safe="/-_.~"
    )
    payload_hash = hashlib.sha256(payload).hexdigest()
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    canonical_headers = (
        f"host:{parsed.netloc}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        (
            "PUT",
            canonical_uri,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        )
    )
    credential_scope = f"{date_stamp}/{s3_region}/s3/aws4_request"
    string_to_sign = "\n".join(
        (
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        )
    )

    def sign(key: bytes, value: str) -> bytes:
        return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()

    date_key = sign(("AWS4" + s3_secret_key).encode("utf-8"), date_stamp)
    region_key = sign(date_key, s3_region)
    service_key = sign(region_key, "s3")
    signing_key = sign(service_key, "aws4_request")
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={s3_access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    request = urllib.request.Request(
        f"{parsed.scheme}://{parsed.netloc}{canonical_uri}",
        data=payload,
        method="PUT",
        headers={
            "Authorization": authorization,
            "Host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        },
    )
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(request, context=context, timeout=60) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f"S3 upload failed with HTTP {response.status}")

    published_model.metadata["artifact_name"] = "carido-model.joblib"
    published_model.metadata["framework"] = "scikit-learn"
    published_model.metadata["s3_bucket"] = s3_bucket
    published_model.metadata["s3_key"] = s3_key


# TODO(student): Declare a pipeline named "carido-training-pipeline" and compose
# the four provided components in this order:
# generate_data -> preprocess_data -> train_model -> save_model.
#
# TODO(student): Compile that pipeline with compiler.Compiler() to the file
# "carido-training-pipeline.yaml".  The component implementations above are
# input fixture code; the graph and compile entry point are intentionally absent.
