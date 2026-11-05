"""Synthetic KFP v2 pipeline input for EX267 Task 03.

The validate/train/evaluate shape is adapted for RHOAI 3.3 from the public
RedHatTraining/AI26X-apps pipeline examples.  The candidate still compiles,
imports, runs, compares, and records the evidence required by the problem.
"""

from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Metrics, Model, Output

BASE_IMAGE = "registry.access.redhat.com/ubi9/python-312:9.6"
PACKAGES = ["pandas==2.2.3", "scikit-learn==1.5.2", "joblib==1.4.2"]


@dsl.component(base_image=BASE_IMAGE, packages_to_install=PACKAGES)
def validate(source: Input[Dataset], validated: Output[Dataset]) -> int:
    import pandas as pd

    frame = pd.read_csv(source.path)
    required = {"transaction_id", "amount", "country", "account_age_days", "failed_logins", "label"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    if set(frame["label"].unique()) != {0, 1}:
        raise ValueError("the synthetic dataset must contain both classes")
    frame.to_csv(validated.path, index=False)
    return len(frame)


@dsl.component(base_image=BASE_IMAGE, packages_to_install=PACKAGES)
def train(validated: Input[Dataset], max_depth: int, model: Output[Model], train_metrics: Output[Metrics]):
    import joblib
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder
    from sklearn.tree import DecisionTreeClassifier

    frame = pd.read_csv(validated.path)
    features = frame.drop(columns=["transaction_id", "label"])
    labels = frame["label"]
    preprocessor = ColumnTransformer(
        [("country", OneHotEncoder(handle_unknown="ignore"), ["country"])],
        remainder="passthrough",
    )
    estimator = Pipeline([
        ("preprocess", preprocessor),
        ("classifier", DecisionTreeClassifier(max_depth=max_depth, random_state=267)),
    ])
    estimator.fit(features, labels)
    joblib.dump(estimator, model.path)
    model.metadata["framework"] = "scikit-learn"
    model.metadata["max_depth"] = max_depth
    train_metrics.log_metric("training_accuracy", float(estimator.score(features, labels)))


@dsl.component(base_image=BASE_IMAGE, packages_to_install=PACKAGES)
def evaluate(validated: Input[Dataset], model: Input[Model], metrics: Output[Metrics]):
    import joblib
    import pandas as pd
    from sklearn.metrics import accuracy_score, f1_score

    frame = pd.read_csv(validated.path)
    features = frame.drop(columns=["transaction_id", "label"])
    labels = frame["label"]
    predictions = joblib.load(model.path).predict(features)
    metrics.log_metric("accuracy", float(accuracy_score(labels, predictions)))
    metrics.log_metric("f1", float(f1_score(labels, predictions)))


@dsl.pipeline(name="fraud-training-pipeline")
def fraud_training_pipeline(
    dataset_uri: str = "s3://ex267-task03/data/transactions.csv",
    max_depth: int = 3,
    run_id: str = "replace-with-unique-run-id",
):
    imported = dsl.importer(artifact_uri=dataset_uri, artifact_class=Dataset, reimport=False)
    checked = validate(source=imported.output)
    checked.set_caching_options(False).set_retry(2)
    trained = train(validated=checked.outputs["validated"], max_depth=max_depth)
    trained.set_cpu_request("250m").set_cpu_limit("1").set_memory_request("512Mi").set_memory_limit("1Gi")
    trained.set_caching_options(False).set_retry(2)
    measured = evaluate(validated=checked.outputs["validated"], model=trained.outputs["model"])
    measured.set_caching_options(False).set_retry(2)
    _ = run_id


if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=fraud_training_pipeline,
        package_path="fraud-training-pipeline.yaml",
    )
