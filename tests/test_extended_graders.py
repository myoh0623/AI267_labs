#!/usr/bin/env python3
"""Positive fixtures for candidate-owned grading contracts."""

from __future__ import annotations

import base64
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
GRADE = runpy.run_path(str(ROOT / "scripts" / "grade.py"), run_name="positive_fixture_test")
SHA = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
GIT = "d" * 40


def encoded(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def metadata(name: str, **extra):
    value = {"name": name}
    value.update(extra)
    return value


class FixtureOc:
    def __init__(self):
        self.objects = {}
        self.lists = {}
        self.all_lists = {}
        self.raw_objects = {}

    def add(self, kind, name, value, namespace=None):
        self.objects[(kind, name, namespace)] = value

    def add_list(self, kind, namespace, values):
        self.lists[(kind, namespace)] = values

    def add_all(self, kind, values):
        self.all_lists[kind] = values

    def add_raw(self, path, value):
        self.raw_objects[path] = value

    def get(self, kind, name, namespace=None):
        return self.objects.get((kind, name, namespace))

    def list(self, kind, namespace, selector=None):
        return self.lists.get((kind, namespace), [])

    def list_all(self, kind):
        return self.all_lists.get(kind, [])

    def raw_json(self, path):
        return self.raw_objects.get(path)


def cm(name, data):
    return {"metadata": metadata(name), "data": data}


def secret(name, *, service_account=None):
    annotations = {}
    secret_type = "Opaque"
    if service_account:
        annotations["kubernetes.io/service-account.name"] = service_account
        secret_type = "kubernetes.io/service-account-token"
    return {
        "metadata": metadata(name, annotations=annotations),
        "type": secret_type,
        "data": {
            "AWS_ACCESS_KEY_ID": encoded("access"),
            "AWS_SECRET_ACCESS_KEY": encoded("secret"),
            "AWS_S3_ENDPOINT": encoded("https://minio.example"),
            "AWS_S3_BUCKET": encoded("bucket"),
        },
    }


def task01():
    oc = FixtureOc()
    ns = "ex267-fraud"
    for name, users in {
        "devops-wala": ["developer", "rajan", "punit"],
        "rhoai-exam-admins": ["raja", "andrew"],
    }.items():
        oc.add("group", name, {
            "metadata": metadata(name, labels={"ex267.practice/task": "01"}),
            "users": users,
        })
    oc.add("auth.services.platform.opendatahub.io", "auth", {
        "metadata": metadata("auth"),
        "spec": {"allowedGroups": ["devops-wala"], "adminGroups": ["rhoai-exam-admins"]},
    })
    oc.add("namespace", ns, {"metadata": metadata(ns, labels={
        "team": "northstar-risk", "environment": "exam"
    })})
    oc.add_list("rolebinding", ns, [
        {"roleRef": {"name": "edit"}, "subjects": [{"kind": "User", "name": "developer1"}]},
        {"roleRef": {"name": "edit"}, "subjects": [{"kind": "User", "name": "suraj"}]},
        {"roleRef": {"name": "admin"}, "subjects": [
            {"kind": "User", "name": "rajan"}, {"kind": "User", "name": "punit"}
        ]},
    ])
    s3 = secret("fraud-s3")
    s3["metadata"]["annotations"]["opendatahub.io/connection-type-protocol"] = "s3"
    oc.add("secret", "fraud-s3", s3, ns)
    oc.add("secret", "exam-provided-minio", secret("exam-provided-minio"), ns)
    oc.add("configmap", "fraud-s3-evidence", cm("fraud-s3-evidence", {
        "input_key": "input/transactions.csv", "output_key": "output/result.json",
        "input_sha256": SHA, "output_sha256": SHA_B, "verified_from_new_process": "true",
    }), ns)
    return oc, ns


def notebook(name, image, claim, requests=None, limits=None, env_from=None):
    return {
        "metadata": metadata(name),
        "spec": {"template": {"spec": {
            "containers": [{
                "image": image,
                "resources": {"requests": requests or {}, "limits": limits or {}},
                "volumeMounts": [{"name": "workspace", "mountPath": "/opt/app-root/src"}],
                "envFrom": env_from or [],
            }],
            "volumes": [{"name": "workspace", "persistentVolumeClaim": {"claimName": claim}}],
        }}},
    }


def profile(name, cpu_min, cpu_max, mem_min, mem_max):
    return {"metadata": metadata(name), "spec": {"identifiers": [
        {"identifier": "cpu", "minCount": cpu_min, "maxCount": cpu_max},
        {"identifier": "memory", "minCount": mem_min, "maxCount": mem_max},
    ]}}


def task02():
    oc = FixtureOc()
    ns = "ex267-t02-workbench"
    oc.add("imagestream", "custom-workbench", {
        "metadata": metadata("custom-workbench", labels={"opendatahub.io/notebook-image": "true"}),
        "spec": {"tags": [{
            "name": "1.0", "from": {"name": "image-registry/custom-workbench@sha256:" + SHA},
            "annotations": {"opendatahub.io/notebook-python-dependencies":
                            "seaborn 0.12.2, python-json-logger 2.0.7"},
        }]},
    }, ns)
    oc.add("notebook", "risk-lab", notebook(
        "risk-lab", "image-registry/custom-workbench:1.0", "risk-lab-storage",
        {"cpu": "1", "memory": "1Gi"}, {"cpu": "2", "memory": "2Gi"},
        [{"secretRef": {"name": "projects-data-connection"}}],
    ) | {"metadata": metadata("risk-lab", annotations={
        "opendatahub.io/connections": "projects-data-connection"
    })}, ns)
    oc.add("configmap", "custom-image-evidence", cm("custom-image-evidence", {
        "build_name": "custom-workbench-1", "image_digest": SHA,
        "seaborn_version": "0.12.2", "python_json_logger_version": "2.0.7",
        "idle_culling_endpoint_verified": "true",
    }), ns)
    culler = cm("notebook-controller-culler-config", {
        "ENABLE_CULLING": "true", "CULL_IDLE_TIME": "240", "IDLENESS_CHECK_PERIOD": "1",
    })
    culler["metadata"]["labels"] = {"ex267.practice/task": "02"}
    oc.add("configmap", "notebook-controller-culler-config", culler, "redhat-ods-applications")
    oc.add("pvc", "risk-lab-storage", {
        "spec": {"resources": {"requests": {"storage": "10Gi"}}}
    }, ns)
    oc.add("hardwareprofile", "medium-small", profile("medium-small", "1", "2", "16Gi", "16Gi"), ns)
    oc.add("hardwareprofile", "my-medium", profile("my-medium", "1", "2", "1Gi", "2Gi"), ns)
    oc.add("notebook", "git-experiments", notebook(
        "git-experiments", "registry/cuda-workbench:2025.2", "git-experiments-storage",
        env_from=[{"configMapRef": {"name": "git-experiments-env"}}],
    ), ns)
    oc.add("configmap", "git-experiments-env", cm("git-experiments-env", {"RANDOM_SIZE": "40"}), ns)
    oc.add("configmap", "workbench-admin-evidence", cm("workbench-admin-evidence", {
        "selected_image": "cuda", "random_size": "40", "stopped_after_test": "true",
    }), ns)
    oc.add("configmap", "git-collaboration-evidence", cm("git-collaboration-evidence", {
        "repository": "https://github.com/RedHatTraining/AI26X-apps",
        "source_branch": "RHOAI3.3", "feature_branch": "experiment",
        "feature_commit": GIT, "merge_commit": "e" * 40,
        "experiment_notebook_sha256": SHA_B, "clean_worktree": "true",
    }), ns)
    s3 = secret("projects-data-connection")
    s3["metadata"]["annotations"]["opendatahub.io/connection-type-protocol"] = "s3"
    oc.add("secret", "projects-data-connection", s3, ns)
    oc.add("configmap", "workbench-s3-evidence", cm("workbench-s3-evidence", {
        "upload_key": "results/a.json", "download_sha256": SHA_C,
        "verified_from_workbench": "true",
    }), ns)
    oc.add("configmap", "workbench-evidence", cm("workbench-evidence", {
        "git_revision": GIT, "data_version": "synthetic-v1", "seed": "42",
        "image_digest": SHA, "artifact_uri": "s3://bucket/model.joblib",
        "tensorboard_runs": "2", "restart_proof": "true",
    }), ns)
    return oc, ns


def workflow(name, *, depth=None, scheduled=False):
    labels = {}
    if depth is not None:
        labels["ex267.io/max-depth"] = str(depth)
    if scheduled:
        labels["ex267.io/scheduled-run"] = "true"
    return {"metadata": metadata(name, labels=labels), "status": {"phase": "Succeeded"}}


def task03():
    oc = FixtureOc()
    ns = "ex267-t03-pipeline"
    oc.add("dspa", "dspa", {"status": {"conditions": [{"type": "Ready", "status": "True"}]}}, ns)
    oc.add("configmap", "fraud-training-pipeline", {
        "metadata": metadata("fraud-training-pipeline", annotations={"ex267.io/kfp-sdk": "2.15.2"}),
        "data": {"compiled-pipeline.yaml": "validate train evaluate"},
    }, ns)
    oc.add("configmap", "pipeline-evidence", cm("pipeline-evidence", {
        "service_account": "pipeline-runner", "secret_name": "aws-connection-fraud-s3",
        "resources_verified": "true", "cache_policy": "disabled",
        "retry_policy": "2", "artifact_prefix_pattern": "runs/{run_id}",
        "approved_model_uri": "s3://bucket/models/approved", "approved_model_sha256": SHA,
    }), ns)
    workflows = [
        workflow("fraud-depth-3", depth=3), workflow("fraud-depth-7", depth=7),
        workflow("tas1-devops-wala-scheduled-1", scheduled=True), workflow("issues-prediction-123"),
    ]
    oc.add_list("workflow", ns, workflows)
    oc.add_list("scheduledworkflow", ns, [{"metadata": metadata("tas1-devops-wala-s1")}])
    oc.add_list("cronworkflow", ns, [])
    oc.add("configmap", "schedule-evidence", cm("schedule-evidence", {
        "pipeline_name": "tas1-devops-wala", "schedule_name": "tas1-devops-wala-s1",
        "interval_seconds": "300", "enabled": "true", "observed_run": "tas1-devops-wala-scheduled-1",
    }), ns)
    oc.add("notebook", "pipelines-elyra-wb", notebook(
        "pipelines-elyra-wb", "registry/jupyter-datascience-cpu:2025.2", "pipelines-elyra-wb"
    ), ns)
    oc.add("pvc", "pipelines-elyra-wb", {
        "spec": {"resources": {"requests": {"storage": "10Gi"}}}
    }, ns)
    oc.add("configmap", "elyra-evidence", cm("elyra-evidence", {
        "pipeline_file": "issues_prediction.pipeline", "workbench_name": "pipelines-elyra-wb",
        "workbench_pvc": "pipelines-elyra-wb",
        "runtime_image": "quay.io/redhattraining/forecast-pipeline-runtime:1.0",
        "secret_name": "aws-connection-fraud-s3", "git_revision": GIT,
        "workflow_name": "issues-prediction-123", "data_csv_sha256": SHA,
        "clean_data_csv_sha256": SHA_B, "forecast_data_csv_sha256": SHA_C,
    }), ns)
    return oc, ns


def task04():
    oc = FixtureOc()
    ns = "ex267-t04-serving"
    oc.add("inferenceservice", "fraud-v2", {
        "metadata": metadata("fraud-v2", annotations={
            "opendatahub.io/connection-path": "models/fraud/2/",
            "ex267.io/model-sha256": SHA,
            "serving.kserve.io/deploymentMode": "RawDeployment",
        }),
        "spec": {"predictor": {"model": {
            "storageUri": "s3://bucket/models/fraud/2/", "runtime": "kserve-ovms",
            "modelFormat": {"name": "onnx"},
            "resources": {"requests": {"cpu": "1", "memory": "2Gi"},
                          "limits": {"cpu": "1", "memory": "2Gi"}},
        }}},
        "status": {"url": "https://fraud-v2.example", "conditions": [{"type": "Ready", "status": "True"}]},
    }, ns)
    oc.add("configmap", "serving-evidence", cm("serving-evidence", {
        "normal_http": "200", "invalid_shape_http": "400",
        "response_schema_sha256": SHA, "invalid_response_sha256": SHA_B,
        "recreated": "true", "rollback_verified": "true", "rollback_model_sha256": SHA_C,
    }), ns)
    oc.add("servingruntime", "fraud-custom-runtime", {
        "spec": {
            "containers": [{"image": "registry/mlserver@sha256:" + SHA}],
            "supportedModelFormats": [{"name": "sklearn"}], "protocolVersions": ["v2"],
        }
    }, ns)
    oc.add("configmap", "custom-runtime-evidence", cm("custom-runtime-evidence", {
        "runtime_name": "fraud-custom-runtime", "runtime_image_digest": SHA,
        "supported_format": "sklearn", "validation_http": "200",
    }), ns)
    oc.add("route", "fraud-v2", {"spec": {"host": "fraud-v2.apps.example"}}, ns)
    oc.add("serviceaccount", "infer-serviceaccount", {"metadata": metadata("infer-serviceaccount")}, ns)
    oc.add("secret", "infer-serviceaccount-token", secret(
        "infer-serviceaccount-token", service_account="infer-serviceaccount"
    ), ns)
    oc.add("configmap", "serving-mode-evidence", cm("serving-mode-evidence", {
        "legacy_multimodel_status": "mapped-to-rhoai-3.3-rawdeployment",
        "current_deployment_mode": "RawDeployment", "external_route": "fraud-v2.apps.example",
        "token_service_account": "infer-serviceaccount", "token_secret": "infer-serviceaccount-token",
        "authenticated_http": "200", "unauthenticated_http": "401", "public_http": "200",
    }), ns)
    return oc, ns


def task06():
    oc = FixtureOc()
    ns = "ex267-t06-registry"
    registry_ns = "rhoai-model-registries"
    service = "redhattraining-model-registry"
    api_path = "/api/model_registry/v1alpha3"
    proxy = f"/api/v1/namespaces/{registry_ns}/services/{service}:http-api/proxy{api_path}"
    properties = {
        "git_revision": {"string_value": GIT},
        "data_reference": {"string_value": "transactions-v1"},
        "pipeline_run": {"string_value": "fraud-run-42"},
        "metrics": {"string_value": "auc=0.94"},
        "intended_use": {"string_value": "fraud screening"},
        "limitations": {"string_value": "synthetic data"},
        "owner": {"string_value": "northstar-risk"},
        "approval": {"string_value": "approved"},
    }
    model = {"id": "model-42", "name": "fraud-risk", "owner": "northstar-risk",
             "customProperties": properties}
    version_1 = {"id": "version-100", "name": "1.0.0", "registeredModelId": "model-42"}
    version_2 = {"id": "version-110", "name": "1.1.0", "registeredModelId": "model-42",
                 "customProperties": properties}
    artifact_1 = {"id": "artifact-100", "modelFormatName": "onnx",
                  "uri": "oci://registry.lab.example.com:8443/redhattraining/models/fraud-risk@sha256:" + SHA}
    artifact_2 = {"id": "artifact-110", "modelFormatName": "onnx",
                  "uri": "oci://registry.lab.example.com:8443/redhattraining/models/fraud-risk@sha256:" + SHA_B}
    oc.add("configmap", "exam-provided-registry-inputs", cm("exam-provided-registry-inputs", {
        "registry_namespace": registry_ns, "registry_service": service,
        "registry_service_port": "http-api", "registry_rest_api": api_path,
        "registry_name": service,
        "oci_registry": "registry.lab.example.com:8443",
        "oci_repository": "redhattraining/models/fraud-risk",
    }), ns)
    oc.add_raw(proxy + "/registered_models", {"items": [model]})
    oc.add_raw(proxy + "/registered_models/model-42/versions", {"items": [version_1, version_2]})
    oc.add_raw(proxy + "/model_versions/version-100/artifacts", {"items": [artifact_1]})
    oc.add_raw(proxy + "/model_versions/version-110/artifacts", {"items": [artifact_2]})
    oc.add("configmap", "registry-evidence", cm("registry-evidence", {
        "model_id": "model-42", "version_1_0_id": "version-100",
        "version_1_1_id": "version-110", "oci_digest_1_0": SHA,
        "oci_digest_1_1": SHA_B, "pulled_artifact_sha256": SHA_C,
        "git_revision": GIT, "data_reference": "transactions-v1",
        "pipeline_run": "fraud-run-42", "format": "onnx",
        "metrics": "auc=0.94", "intended_use": "fraud screening",
        "limitations": "synthetic data", "owner": "northstar-risk",
        "approval": "approved", "registry_api_path": api_path,
        "registry_api_response_sha256": SHA, "deployed_version": "1.1.0",
        "deployment_artifact_digest": SHA_B,
    }), ns)
    oc.add_list("inferenceservice", ns, [{
        "metadata": metadata("fraud-risk", labels={
            "modelregistry.opendatahub.io/registered-model-id": "model-42",
            "modelregistry.opendatahub.io/model-version-id": "version-110",
            "modelregistry.opendatahub.io/name": service,
        }, annotations={"ex267.io/model-artifact-digest": "sha256:" + SHA_B}),
        "spec": {"predictor": {"model": {
            "storageUri": "oci://registry.lab.example.com:8443/redhattraining/models/fraud-risk@sha256:" + SHA_B,
        }}},
        "status": {"conditions": [{"type": "Ready", "status": "True"}]},
    }])
    return oc, ns


def task09():
    oc = FixtureOc()
    ns = "ex267-t09-rag"
    oc.add("configmap", "rag-evidence", cm("rag-evidence", {
        "source_id": "ai267-chapter09-docs", "source_revision": "synthetic-v1",
        "document_acl": "public/restricted", "embedding_model_revision": "hash-v1",
        "index_digest": SHA, "unauthorized_retrieval_count": "0",
        "stream_http": "200", "citation_response_sha256": SHA_B,
        "tool_schema_sha256": SHA_C, "tool_read_only": "true",
        "tool_timeout_seconds": "5", "tool_step_limit": "3",
        "tool_audit_sha256": SHA,
        "direct_injection": "pass", "indirect_injection": "pass",
        "unauthorized_document": "pass", "malformed_tool_argument": "pass",
        "dependency_outage": "pass", "false_positive_test": "pass",
    }), ns)
    oc.add("role", "rag-reader", {
        "metadata": metadata("rag-reader"),
        "rules": [{
            "apiGroups": [""], "resources": ["configmaps"],
            "resourceNames": ["rag-documents"], "verbs": ["get"],
        }],
    }, ns)
    oc.add_list("networkpolicy", ns, [{
        "metadata": metadata("rag-egress"),
        "spec": {
            "podSelector": {"matchLabels": {"app": "genai-app"}},
            "policyTypes": ["Egress"],
            "egress": [
                {"to": [{"podSelector": {"matchLabels": {"app": "mock-llm"}}}],
                 "ports": [{"protocol": "TCP", "port": 8080}]},
                {"to": [{"podSelector": {"matchLabels": {"app": "todo-tool"}}}],
                 "ports": [{"protocol": "TCP", "port": 8080}]},
                {"to": [{"namespaceSelector": {"matchLabels": {
                    "kubernetes.io/metadata.name": "openshift-dns"
                }}}], "ports": [{"protocol": "UDP", "port": 53},
                                  {"protocol": "TCP", "port": 53}]},
            ],
        },
    }])
    oc.add_list("rolebinding", ns, [{
        "roleRef": {"kind": "Role", "name": "rag-reader"},
        "subjects": [{"kind": "ServiceAccount", "name": "rag-app", "namespace": ns}],
    }])
    verifier_source = (ROOT / "tasks" / "09-rag" / "inputs" / "verify_rag.py").read_text()
    oc.add("configmap", "exam-provided-rag-verifier", cm(
        "exam-provided-rag-verifier", {"verify_rag.py": verifier_source}
    ), ns)
    oc.add("job", "rag-contract-verification", {
        "metadata": metadata("rag-contract-verification"),
        "spec": {"template": {"spec": {
            "containers": [{
                "image": "registry.access.redhat.com/ubi9/python-312:9.6",
                "command": ["python", "/verify/verify_rag.py"],
                "volumeMounts": [{"name": "verifier", "mountPath": "/verify", "readOnly": True}],
            }],
            "volumes": [{"name": "verifier", "configMap": {
                "name": "exam-provided-rag-verifier"
            }}],
        }}},
        "status": {"succeeded": 1, "conditions": [{"type": "Complete", "status": "True"}]},
    }, ns)
    return oc, ns


def failed_checks(task, oc, namespace):
    return {
        item.check_id
        for item in GRADE["GRADERS"][task](oc, namespace)
        if not item.passed
    }


def negative_contracts():
    oc, ns = task01()
    oc.objects[("group", "devops-wala", None)]["metadata"]["labels"] = {}
    assert "01-1" in failed_checks("01", oc, ns)

    oc, ns = task01()
    oc.objects[("auth.services.platform.opendatahub.io", "auth", None)]["spec"]["allowedGroups"].append(
        "system:authenticated"
    )
    assert {"01-1", "01-7"}.issubset(failed_checks("01", oc, ns))

    oc, ns = task01()
    oc.lists[("rolebinding", ns)][0]["roleRef"]["name"] = "admin"
    assert "01-3" in failed_checks("01", oc, ns)

    oc, ns = task01()
    oc.objects[("secret", "fraud-s3", ns)]["data"]["AWS_S3_BUCKET"] = encoded("wrong-bucket")
    assert "01-5" in failed_checks("01", oc, ns)

    oc, ns = task06()
    oc.raw_objects.clear()
    assert {"06-1", "06-2", "06-3", "06-4", "06-5"} == failed_checks("06", oc, ns)

    oc, ns = task06()
    oc.objects[("configmap", "registry-evidence", ns)]["data"]["model_id"] = "wrong-model"
    assert "06-1" in failed_checks("06", oc, ns)

    oc, ns = task06()
    path = next(path for path in oc.raw_objects if path.endswith("version-110/artifacts"))
    oc.raw_objects[path]["items"][0]["uri"] = "oci://wrong.example/model@sha256:" + SHA_B
    assert "06-2" in failed_checks("06", oc, ns)

    oc, ns = task09()
    del oc.objects[("role", "rag-reader", ns)]
    assert "09-2" in failed_checks("09", oc, ns)

    oc, ns = task09()
    oc.lists[("networkpolicy", ns)][0]["spec"]["egress"] = [{}]
    assert "09-2" in failed_checks("09", oc, ns)

    oc, ns = task09()
    del oc.objects[("job", "rag-contract-verification", ns)]
    assert {"09-3", "09-4", "09-5"}.issubset(failed_checks("09", oc, ns))

    print("[validate] Task 01, 06, 09 negative grading contracts passed")


def main():
    for task, factory in (
        ("01", task01), ("02", task02), ("03", task03),
        ("04", task04), ("06", task06), ("09", task09),
    ):
        oc, namespace = factory()
        results = GRADE["GRADERS"][task](oc, namespace)
        failed = [item.check_id for item in results if not item.passed]
        assert not failed, (task, failed)
        assert sum(item.points for item in results) == GRADE["TASKS"][task][1]
    negative_contracts()
    print("[validate] candidate-owned Task 01-04, 06, 09 grader fixtures passed")


if __name__ == "__main__":
    main()

