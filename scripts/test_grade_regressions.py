#!/usr/bin/env python3
"""Regression fixtures for AI267 graders, including Task 05's ephemeral verifier."""

from __future__ import annotations

import base64
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import call, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ai267_grade", ROOT / "scripts" / "grade.py")
assert SPEC and SPEC.loader
grade = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = grade
SPEC.loader.exec_module(grade)


def encoded(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


class FixtureOc:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str, str | None], dict] = {}
        self.lists: dict[tuple[str, str | None], list[dict]] = {}

    def add(self, kind: str, name: str, value: dict, namespace: str | None = None) -> None:
        self.objects[(kind, name, namespace)] = value

    def add_list(self, kind: str, values: list[dict], namespace: str | None = None) -> None:
        self.lists[(kind, namespace)] = values

    def get(self, kind: str, name: str, namespace: str | None = None):
        return self.objects.get((kind, name, namespace))

    def list(self, kind: str, namespace: str | None = None):
        return self.lists.get((kind, namespace), [])


def profile(name: str, display: str, cpu: tuple[str, str, str], memory: tuple[str, str, str]) -> dict:
    return {
        "metadata": {
            "name": name,
            "annotations": {"opendatahub.io/display-name": display},
        },
        "spec": {
            "identifiers": [
                dict(zip(("identifier", "minCount", "defaultCount", "maxCount"), ("cpu", *cpu))),
                dict(zip(("identifier", "minCount", "defaultCount", "maxCount"), ("memory", *memory))),
            ]
        },
    }


def notebook(
    name: str,
    image: str,
    *,
    annotations: dict[str, str] | None = None,
    resources: dict | None = None,
    env_from: list[dict] | None = None,
    claim: str | None = None,
) -> dict:
    volumes = []
    if claim:
        volumes.append({"name": "workspace", "persistentVolumeClaim": {"claimName": claim}})
    return {
        "metadata": {"name": name, "annotations": annotations or {}},
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": name,
                            "image": image,
                            "resources": resources or {},
                            "envFrom": env_from or [],
                        }
                    ],
                    "volumes": volumes,
                }
            }
        },
    }


class TaskFixtureTests(unittest.TestCase):
    def test_task01_happy_fixture_and_suraj_admin_near_miss(self) -> None:
        ns = "my-lab-pro"
        oc = FixtureOc()
        oc.add("namespace", ns, {"metadata": {"name": ns}})
        oc.add(
            "hardwareprofile.infrastructure.opendatahub.io",
            "task01-2cpu-8gi",
            profile(
                "task01-2cpu-8gi",
                "Task 01 - 2 CPU, 8 GiB",
                ("2", "2", "2"),
                ("8Gi", "8Gi", "8Gi"),
            ),
            "redhat-ods-applications",
        )
        oc.add_list(
            "rolebinding.rbac.authorization.k8s.io",
            [
                {"roleRef": {"name": "admin"}, "subjects": [{"kind": "User", "name": "rajan"}]},
                {"roleRef": {"name": "admin"}, "subjects": [{"kind": "User", "name": "punit"}]},
                {"roleRef": {"name": "edit"}, "subjects": [{"kind": "User", "name": "suraj"}]},
            ],
            ns,
        )
        oc.add_list("clusterrolebinding.rbac.authorization.k8s.io", [])
        oc.add(
            "notebook.kubeflow.org",
            "myworkbench-wb",
            notebook(
                "myworkbench-wb",
                "registry/s2i-pytorch-cuda-notebook:latest",
                annotations={
                    "opendatahub.io/image-display-name": "Jupyter | PyTorch | CUDA | Python 3.12",
                    "notebooks.opendatahub.io/last-image-selection": "pytorch:2025.2",
                    "opendatahub.io/hardware-profile-name": "task01-2cpu-8gi",
                    "opendatahub.io/hardware-profile-namespace": "redhat-ods-applications",
                },
                resources={
                    "requests": {"cpu": "2", "memory": "8Gi"},
                    "limits": {"cpu": "2", "memory": "8Gi"},
                },
                env_from=[{"configMapRef": {"name": "myworkbench-env"}}],
                claim="myworkbench-wb-storage",
            ),
            ns,
        )
        oc.add(
            "pvc",
            "myworkbench-wb-storage",
            {"spec": {"resources": {"requests": {"storage": "2Gi"}}}, "status": {"phase": "Bound"}},
            ns,
        )
        oc.add("configmap", "myworkbench-env", {"data": {"var": "devops-wala"}}, ns)

        with patch.object(grade, "git_check", return_value=True):
            results = grade.grader_01(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)

        near_miss = copy.deepcopy(oc)
        near_miss.lists[("rolebinding.rbac.authorization.k8s.io", ns)].append(
            {"roleRef": {"name": "admin"}, "subjects": [{"kind": "User", "name": "suraj"}]}
        )
        with patch.object(grade, "git_check", return_value=True):
            failed = {item.check_id for item in grade.grader_01(near_miss, ns) if not item.passed}
        self.assertIn("01-rbac", failed)

        wrong_image_version = copy.deepcopy(oc)
        wrong_image_version.objects[("notebook.kubeflow.org", "myworkbench-wb", ns)][
            "metadata"
        ]["annotations"]["notebooks.opendatahub.io/last-image-selection"] = "pytorch:2025.1"
        with patch.object(grade, "git_check", return_value=True):
            failed = {
                item.check_id
                for item in grade.grader_01(wrong_image_version, ns)
                if not item.passed
            }
        self.assertIn("01-workbench", failed)

        missing_project = copy.deepcopy(oc)
        del missing_project.objects[("namespace", ns, None)]
        with patch.object(grade, "git_check", return_value=True):
            failed = {
                item.check_id
                for item in grade.grader_01(missing_project, ns)
                if not item.passed
            }
        self.assertIn("01-workbench", failed)

    def test_task02_happy_fixture_and_group_isolation_near_misses(self) -> None:
        oc = FixtureOc()
        oc.add(
            "group.user.openshift.io",
            "devops-wala",
            {"metadata": {"name": "devops-wala"}, "users": ["developer", "rajan", "punit"]},
        )
        oc.add(
            "group.user.openshift.io",
            "ai267-admins",
            {"metadata": {"name": "ai267-admins"}, "users": ["suraj", "raja", "andrew"]},
        )
        oc.add(
            "auth.services.platform.opendatahub.io",
            "auth",
            {"spec": {"allowedGroups": ["devops-wala"], "adminGroups": ["ai267-admins"]}},
        )
        oc.add_list("clusterrolebinding.rbac.authorization.k8s.io", [])
        results = grade.grader_02(oc, "intro-projects")
        self.assertTrue(all(item.passed for item in results), results)

        other_group = copy.deepcopy(oc)
        other_group.add_list(
            "group.user.openshift.io",
            [{"metadata": {"name": "another-team"}, "users": ["rajan"]}],
        )
        failed = {
            item.check_id for item in grade.grader_02(other_group, "intro-projects") if not item.passed
        }
        self.assertIn("02-isolation", failed)

        broken = copy.deepcopy(oc)
        broken.add_list(
            "clusterrolebinding.rbac.authorization.k8s.io",
            [
                {
                    "roleRef": {"name": "cluster-admin"},
                    "subjects": [{"kind": "User", "name": "developer"}],
                }
            ],
        )
        failed = {item.check_id for item in grade.grader_02(broken, "intro-projects") if not item.passed}
        self.assertTrue({"02-isolation", "02-no-broad-admin"} <= failed)

    def test_task03_accepts_real_image_name_and_rejects_wrong_profile(self) -> None:
        ns = "workbench-creating"
        oc = FixtureOc()
        oc.add(
            "hardwareprofile.infrastructure.opendatahub.io",
            "medium-small",
            profile("medium-small", "MediumSmall", ("1", "1", "2"), ("16Gi", "16Gi", "16Gi")),
            ns,
        )
        oc.add(
            "hardwareprofile.infrastructure.opendatahub.io",
            "my-medium",
            profile("my-medium", "My-medium", ("1", "1", "2"), ("1Gi", "1Gi", "2Gi")),
            ns,
        )
        oc.add(
            "hardwareprofile.infrastructure.opendatahub.io",
            "small",
            profile("small", "Small", ("1", "1", "2"), ("2Gi", "2Gi", "8Gi")),
            "redhat-ods-applications",
        )
        oc.add(
            "notebook.kubeflow.org",
            "manage-resources-wb",
            notebook(
                "manage-resources-wb",
                "registry/s2i-generic-data-science-notebook:2026.1",
                annotations={
                    "opendatahub.io/hardware-profile-name": "small",
                    "opendatahub.io/hardware-profile-namespace": "redhat-ods-applications",
                },
            ),
            ns,
        )
        content = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "outputs": [{"output_type": "display_data"}],
                        "source": [
                            "import numpy as np\n",
                            "import plotly.express as px\n",
                            "x = np.linspace(start=-50, stop=50)\n",
                            "y = x ** 2\n",
                            "fig = px.scatter(x=x, y=y)\n",
                            "fig.show()\n",
                        ],
                    }
                ]
            }
        )
        with (
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_stdout", return_value=content),
        ):
            results = grade.grader_03(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)

        broken = copy.deepcopy(oc)
        broken.objects[("notebook.kubeflow.org", "manage-resources-wb", ns)]["metadata"]["annotations"][
            "opendatahub.io/hardware-profile-name"
        ] = "my-medium"
        with (
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_stdout", return_value=content),
        ):
            failed = {item.check_id for item in grade.grader_03(broken, ns) if not item.passed}
        self.assertIn("03-workbench", failed)

        medium_small = copy.deepcopy(oc)
        medium_small.objects[(
            "notebook.kubeflow.org",
            "manage-resources-wb",
            ns,
        )]["metadata"]["annotations"].update(
            {
                "opendatahub.io/hardware-profile-name": "medium-small",
                "opendatahub.io/hardware-profile-namespace": ns,
            }
        )
        with (
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_stdout", return_value=content),
        ):
            failed = {
                item.check_id
                for item in grade.grader_03(medium_small, ns)
                if not item.passed
            }
        self.assertIn("03-workbench", failed)

        def git_without_committed_notebook(
            _oc: FixtureOc, _namespace: str, _notebook: str, expression: str
        ) -> bool:
            return "cat-file -e experiment:workbench/working/experiment1.ipynb" not in expression

        with (
            patch.object(grade, "git_check", side_effect=git_without_committed_notebook),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_stdout", return_value=content),
        ):
            failed = {item.check_id for item in grade.grader_03(oc, ns) if not item.passed}
        self.assertIn("03-merge", failed)

        wrong_range = content.replace("stop=50", "stop=5")
        with (
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_stdout", return_value=wrong_range),
        ):
            failed = {item.check_id for item in grade.grader_03(oc, ns) if not item.passed}
        self.assertIn("03-notebook", failed)

        missing_show = content.replace("fig.show()", "fig.write_html('plot.html')")
        with (
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_stdout", return_value=missing_show),
        ):
            failed = {item.check_id for item in grade.grader_03(oc, ns) if not item.passed}
        self.assertIn("03-notebook", failed)

    def test_task04_happy_fixture_and_wrong_endpoint_near_miss(self) -> None:
        ns = "projects-data"
        oc = FixtureOc()
        secret = {
            "metadata": {"annotations": {"opendatahub.io/connection-type-protocol": "s3"}},
            "data": {
                "AWS_ACCESS_KEY_ID": encoded("minio"),
                "AWS_SECRET_ACCESS_KEY": encoded("minio123"),
                "AWS_S3_ENDPOINT": encoded("https://minio-api-minio.apps.lab.example.com"),
                "AWS_DEFAULT_REGION": encoded("us-east-1"),
                "AWS_S3_BUCKET": encoded("projects-data-bucket"),
            },
        }
        oc.add("secret", "projects-data-connection", secret, ns)
        oc.add(
            "notebook.kubeflow.org",
            "projects-data-wb",
            notebook(
                "projects-data-wb",
                "registry/s2i-generic-data-science-notebook:2026.1",
                annotations={
                    "opendatahub.io/image-display-name": "Jupyter | Data Science | CPU | Python 3.12",
                    "opendatahub.io/connections": '["projects-data-connection"]',
                },
            ),
            ns,
        )
        notebook_content = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": [
                            's3.upload_file("dataset.csv", bucket_name, "dataset.csv")\n',
                            's3.download_file(bucket_name, "dataset.csv", "downloaded-dataset.csv")\n',
                        ],
                        "execution_count": 1,
                        "outputs": [],
                    }
                ]
            }
        )
        with (
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=notebook_content),
            patch.object(grade, "exec_ok", return_value=True),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            results = grade.grader_04(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)

        broken = copy.deepcopy(oc)
        broken.objects[("secret", "projects-data-connection", ns)]["data"][
            "AWS_S3_ENDPOINT"
        ] = encoded("https://wrong.example.com")
        with (
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=notebook_content),
            patch.object(grade, "exec_ok", return_value=True),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_04(broken, ns) if not item.passed}
        self.assertIn("04-connection", failed)

        unexecuted = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": [
                            's3.upload_file("dataset.csv", bucket_name, "dataset.csv")\n',
                            's3.download_file(bucket_name, "dataset.csv", "downloaded-dataset.csv")\n',
                        ],
                        "execution_count": None,
                        "outputs": [],
                    }
                ]
            }
        )
        with (
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=unexecuted),
            patch.object(grade, "exec_ok", return_value=True),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {
                item.check_id for item in grade.grader_04(oc, ns) if not item.passed
            }
        self.assertIn("04-download", failed)

    def test_task05_happy_fixture_and_detached_configmap_near_miss(self) -> None:
        ns = "workbench-working"
        oc = FixtureOc()
        wb = notebook(
            "model-training",
            "registry/s2i-pytorch-cuda-notebook:latest",
            annotations={
                "opendatahub.io/image-display-name": "Jupyter | PyTorch | CUDA | Python 3.12",
                "kubeflow-resource-stopped": "2026-11-07T00:00:00Z",
            },
            env_from=[{"configMapRef": {"name": "model-training-env"}}],
        )
        oc.add("notebook.kubeflow.org", "model-training", wb, ns)
        oc.add("configmap", "model-training-env", {"data": {"RANDOM_SIZE": "40"}}, ns)
        with patch.object(
            grade,
            "stopped_notebook_repo_checks",
            return_value=(True, True, True),
        ):
            results = grade.grader_05(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)

        broken = copy.deepcopy(oc)
        broken.objects[("notebook.kubeflow.org", "model-training", ns)]["spec"]["template"]["spec"][
            "containers"
        ][0]["envFrom"] = []
        with patch.object(
            grade,
            "stopped_notebook_repo_checks",
            return_value=(True, True, True),
        ):
            failed = {item.check_id for item in grade.grader_05(broken, ns) if not item.passed}
        self.assertIn("05-env", failed)

        running = copy.deepcopy(oc)
        del running.objects[("notebook.kubeflow.org", "model-training", ns)]["metadata"][
            "annotations"
        ]["kubeflow-resource-stopped"]
        with patch.object(
            grade,
            "stopped_notebook_repo_checks",
            return_value=(True, True, True),
        ) as inspect:
            failed = {item.check_id for item in grade.grader_05(running, ns) if not item.passed}
        self.assertIn("05-stopped", failed)
        self.assertIn("05-repo", failed)
        inspect.assert_not_called()

    def test_task09_happy_fixture_and_auth_near_miss(self) -> None:
        ns = "tiger"
        oc = FixtureOc()
        oc.add("namespace", ns, {"metadata": {"name": ns}})
        oc.add(
            "secret",
            "rhoaiserving-using",
            {
                "metadata": {"annotations": {"opendatahub.io/connection-type-protocol": "s3"}},
                "data": {
                    "AWS_ACCESS_KEY_ID": encoded("minio"),
                    "AWS_SECRET_ACCESS_KEY": encoded("minio123"),
                    "AWS_S3_ENDPOINT": encoded("https://minio-api-minio.apps.lab.example.com"),
                    "AWS_DEFAULT_REGION": encoded("us-east-1"),
                    "AWS_S3_BUCKET": encoded("models-bucket"),
                },
            },
            ns,
        )
        oc.add(
            "inferenceservice.serving.kserve.io",
            "diabetes",
            {
                "metadata": {
                    "name": "diabetes",
                    "annotations": {
                        "serving.kserve.io/deploymentMode": "RawDeployment",
                        "security.opendatahub.io/enable-auth": "false",
                    },
                },
                "spec": {
                    "predictor": {
                        "model": {
                            "modelFormat": {"name": "onnx", "version": "1"},
                            "runtime": "diabetes-openvino",
                            "storage": {
                                "key": "rhoaiserving-using",
                                "path": "models/diabetes",
                            },
                        }
                    }
                },
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            },
            ns,
        )
        oc.add(
            "servingruntime.serving.kserve.io",
            "diabetes-openvino",
            {
                "metadata": {
                    "name": "diabetes-openvino",
                    "annotations": {"openshift.io/display-name": "OpenVINO Model Server"},
                },
                "spec": {
                    "annotations": {"opendatahub.io/kserve-runtime": "ovms"},
                    "containers": [
                        {
                            "name": "kserve-container",
                            "image": "quay.io/modh/openvino_model_server:latest",
                        }
                    ],
                    "supportedModelFormats": [{"name": "onnx", "version": "1"}],
                },
            },
            ns,
        )
        oc.add_list(
            "route.route.openshift.io",
            [{"metadata": {"name": "diabetes"}, "spec": {"host": "diabetes.apps.lab.example.com"}}],
            ns,
        )
        oc.add_list("secret", [], ns)
        with patch.object(grade, "unauthenticated_v2_inference_ok", return_value=True):
            results = grade.grader_09(oc, "serving-openvino")
        self.assertTrue(all(item.passed for item in results), results)

        broken = copy.deepcopy(oc)
        broken.objects[("inferenceservice.serving.kserve.io", "diabetes", ns)]["metadata"]["annotations"][
            "security.opendatahub.io/enable-auth"
        ] = "true"
        with patch.object(grade, "unauthenticated_v2_inference_ok", return_value=True):
            failed = {item.check_id for item in grade.grader_09(broken, "serving-openvino") if not item.passed}
        self.assertIn("09-route", failed)

        wrong_runtime = copy.deepcopy(oc)
        runtime = wrong_runtime.objects.pop(
            ("servingruntime.serving.kserve.io", "diabetes-openvino", ns)
        )
        runtime["metadata"]["name"] = "diabetes-triton"
        runtime["metadata"]["annotations"] = {"openshift.io/display-name": "Triton Server"}
        runtime["spec"]["annotations"] = {}
        runtime["spec"]["containers"][0]["image"] = "nvcr.io/nvidia/tritonserver:latest"
        wrong_runtime.objects[
            ("servingruntime.serving.kserve.io", "diabetes-triton", ns)
        ] = runtime
        wrong_runtime.objects[("inferenceservice.serving.kserve.io", "diabetes", ns)]["spec"][
            "predictor"
        ]["model"]["runtime"] = "diabetes-triton"
        with patch.object(grade, "unauthenticated_v2_inference_ok", return_value=True):
            failed = {
                item.check_id
                for item in grade.grader_09(wrong_runtime, "serving-openvino")
                if not item.passed
            }
        self.assertIn("09-spec", failed)

    def test_task08_happy_fixture_and_wrong_bucket_near_miss(self) -> None:
        ns = "workbench-connections"
        oc = FixtureOc()
        secret = {
            "metadata": {"annotations": {"opendatahub.io/connection-type-protocol": "s3"}},
            "data": {
                "AWS_ACCESS_KEY_ID": encoded("minio"),
                "AWS_SECRET_ACCESS_KEY": encoded("minio123"),
                "AWS_S3_ENDPOINT": encoded("https://minio-api-minio.apps.lab.example.com"),
                "AWS_DEFAULT_REGION": encoded("us-east-1"),
                "AWS_S3_BUCKET": encoded("saved-models"),
            },
        }
        oc.add("secret", "my-s3-connection", secret, ns)
        oc.add(
            "notebook.kubeflow.org",
            "workbench-connections-wb",
            notebook(
                "workbench-connections-wb",
                "image",
                annotations={"opendatahub.io/connections": '["my-s3-connection"]'},
            ),
            ns,
        )
        notebook_content = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": [
                            "# saving THE JOBLIB Model file\n",
                            "%run /opt/app-root/src/train_carido_model.py\n",
                            "import joblib\n",
                            "joblib.dump(ml_model, '/opt/app-root/src/AI26X-apps/carido-model.joblib')\n",
                        ],
                        "execution_count": 1,
                        "outputs": [{"output_type": "stream", "text": ["carido-model.joblib\n"]}],
                    },
                    {
                        "cell_type": "code",
                        "source": [
                            "s3.upload_file('./dataset.csv', bucket_name, 'dataset.csv')\n"
                        ],
                        "execution_count": 2,
                        "outputs": [],
                    },
                    {
                        "cell_type": "code",
                        "source": [
                            "s3.download_file(bucket_name, 'dataset.csv', "
                            "'downloaded-dataset.csv')\n"
                        ],
                        "execution_count": 3,
                        "outputs": [],
                    },
                    {
                        "cell_type": "code",
                        "source": [
                            "s3.upload_file('/opt/app-root/src/AI26X-apps/carido-model.joblib', "
                            "bucket_name, 'carido-model.joblib')\n"
                        ],
                        "execution_count": 4,
                        "outputs": [],
                    },
                    {
                        "cell_type": "code",
                        "source": [
                            "s3.download_file(bucket_name, 'carido-model.joblib', "
                            "'/opt/app-root/src/AI26X-apps/downloaded-carido-model.joblib')\n"
                        ],
                        "execution_count": 5,
                        "outputs": [],
                    },
                ]
            }
        )
        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=notebook_content),
            patch.object(
                grade, "s3_object_matches_local", return_value=True
            ) as object_match,
        ):
            results = grade.grader_08(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)
        object_match.assert_has_calls(
            [
                call(
                    oc,
                    ns,
                    "workbench-connections-wb",
                    "/opt/app-root/src/AI26X-apps/workbench/connections/dataset.csv",
                    "dataset.csv",
                    "/opt/app-root/src/AI26X-apps/workbench/connections/downloaded-dataset.csv",
                ),
                call(
                    oc,
                    ns,
                    "workbench-connections-wb",
                    "/opt/app-root/src/AI26X-apps/carido-model.joblib",
                    "carido-model.joblib",
                    "/opt/app-root/src/AI26X-apps/downloaded-carido-model.joblib",
                ),
            ]
        )
        self.assertEqual(object_match.call_count, 2)

        prefixed = copy.deepcopy(oc)
        prefixed_secret = prefixed.objects.pop(("secret", "my-s3-connection", ns))
        prefixed.add(
            "secret",
            "aws-connection-my-s3-connection",
            prefixed_secret,
            ns,
        )
        prefixed.objects[("notebook.kubeflow.org", "workbench-connections-wb", ns)][
            "metadata"
        ]["annotations"]["opendatahub.io/connections"] = (
            '["aws-connection-my-s3-connection"]'
        )
        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=notebook_content),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            results = grade.grader_08(prefixed, ns)
        self.assertTrue(all(item.passed for item in results), results)

        broken = copy.deepcopy(oc)
        broken.objects[("secret", "my-s3-connection", ns)]["data"]["AWS_S3_BUCKET"] = encoded(
            "workbench-connections-bucket"
        )
        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=notebook_content),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_08(broken, ns) if not item.passed}
        self.assertIn("08-connection", failed)

        def git_without_notebook_change(
            _oc: FixtureOc, _namespace: str, _notebook: str, expression: str
        ) -> bool:
            return (
                "diff --quiet origin/RHOAI3.3..experiment2 -- "
                "workbench/connections/workbench-connections.ipynb"
                not in expression
            )

        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", side_effect=git_without_notebook_change),
            patch.object(grade, "exec_stdout", return_value=notebook_content),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_08(oc, ns) if not item.passed}
        self.assertIn("08-branch", failed)

        def git_with_dirty_worktree(
            _oc: FixtureOc, _namespace: str, _notebook: str, expression: str
        ) -> bool:
            return "status --porcelain" not in expression

        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", side_effect=git_with_dirty_worktree),
            patch.object(grade, "exec_stdout", return_value=notebook_content),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_08(oc, ns) if not item.passed}
        self.assertIn("08-merge", failed)

        unexecuted = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": ["joblib.dump(model, 'carido-model.joblib')\n"],
                        "execution_count": None,
                        "outputs": [],
                    }
                ]
            }
        )
        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=unexecuted),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_08(oc, ns) if not item.passed}
        self.assertIn("08-local", failed)

        wrapper_only = json.loads(notebook_content)
        wrapper_only["cells"][0]["source"] = [
            "# saving THE JOBLIB Model file\n",
            "%run /opt/app-root/src/train_carido_model.py\n",
        ]
        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=json.dumps(wrapper_only)),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_08(oc, ns) if not item.passed}
        self.assertIn("08-local", failed)

        no_download = json.loads(notebook_content)
        no_download["cells"] = no_download["cells"][:-1]
        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "exec_stdout", return_value=json.dumps(no_download)),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_08(oc, ns) if not item.passed}
        self.assertIn("08-local", failed)

        no_dataset_upload = json.loads(notebook_content)
        del no_dataset_upload["cells"][1]
        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(
                grade, "exec_stdout", return_value=json.dumps(no_dataset_upload)
            ),
            patch.object(grade, "s3_object_matches_local", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_08(oc, ns) if not item.passed}
        self.assertIn("08-local", failed)

        wrong_download_bytes = json.loads(notebook_content)
        with (
            patch.object(grade, "local_joblib_model_ok", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(
                grade, "exec_stdout", return_value=json.dumps(wrong_download_bytes)
            ),
            patch.object(grade, "s3_object_matches_local", return_value=False),
        ):
            failed = {item.check_id for item in grade.grader_08(oc, ns) if not item.passed}
        self.assertIn("08-object", failed)

    def test_task06_happy_fixture_and_missing_package_near_miss(self) -> None:
        ns = "workbench-custom"
        oc = FixtureOc()
        image_stream = {
            "metadata": {
                "name": "custom-workbench",
                "labels": {"opendatahub.io/notebook-image": "true"},
                "annotations": {"opendatahub.io/notebook-image-name": "custom-workbench"},
            },
            "spec": {
                "tags": [
                    {
                        "from": {
                            "kind": "DockerImage",
                            "name": "registry.lab.example.com:8443/developer/custom-workbench-image:1.0",
                        },
                        "annotations": {
                            "opendatahub.io/notebook-image-desc": "The image provides the seaborn Python package.",
                            "opendatahub.io/notebook-software": json.dumps(
                                [{"name": "Python", "version": "3.12"}]
                            ),
                            "opendatahub.io/notebook-python-dependencies": json.dumps(
                                [
                                    {"name": "seaborn", "version": "0.13.2"},
                                    {"name": "python-json-logger", "version": "2.0.7"},
                                ]
                            ),
                        },
                    }
                ]
            },
        }
        oc.add_list("imagestream.image.openshift.io", [image_stream], "redhat-ods-applications")
        oc.add(
            "notebook.kubeflow.org",
            "custom-wb",
            notebook(
                "custom-wb",
                "image-registry/custom-workbench:1.0",
                annotations={"opendatahub.io/image-display-name": "custom-workbench"},
            ),
            ns,
        )
        with (
            patch.object(grade, "requirement_pinned", return_value=True),
            patch.object(grade, "local_image_tags_same", return_value=True),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_ok", return_value=True),
        ):
            results = grade.grader_06(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)

        broken = copy.deepcopy(oc)
        dependency_key = "opendatahub.io/notebook-python-dependencies"
        broken.lists[("imagestream.image.openshift.io", "redhat-ods-applications")][0]["spec"]["tags"][0][
            "annotations"
        ][dependency_key] = json.dumps([{"name": "seaborn", "version": "0.13.2"}])
        with (
            patch.object(grade, "requirement_pinned", return_value=True),
            patch.object(grade, "local_image_tags_same", return_value=True),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_ok", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_06(broken, ns) if not item.passed}
        self.assertIn("06-metadata", failed)

        with (
            patch.object(grade, "requirement_pinned", return_value=True),
            patch.object(grade, "local_image_tags_same", return_value=False),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "exec_ok", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_06(oc, ns) if not item.passed}
        self.assertIn("06-build", failed)

    def test_task07_happy_fixture_and_generic_branch_near_misses(self) -> None:
        ns = "workbench-working"
        branch = "feature/team-notebook"
        candidate = {"branch": branch, "paths": ["notes/collaboration.ipynb"]}
        evidence = {
            "repository": True,
            "feature_branches": [branch],
            "notebook_candidates": [candidate],
            "merged_candidates": [candidate],
            "clean": True,
        }
        with (
            patch.object(grade, "task07_git_evidence", return_value=evidence),
            patch.object(grade, "pod_is_ready", return_value=True),
        ):
            results = grade.grader_07(FixtureOc(), ns)
        self.assertTrue(all(item.passed for item in results), results)

        baseline_only = {
            "repository": True,
            "feature_branches": [],
            "notebook_candidates": [
                {"branch": "RHOAI3.3", "paths": ["workbench/working/train_model.ipynb"]}
            ],
            "merged_candidates": [
                {"branch": "RHOAI3.3", "paths": ["workbench/working/train_model.ipynb"]}
            ],
            "clean": True,
        }
        with (
            patch.object(grade, "task07_git_evidence", return_value=baseline_only),
            patch.object(grade, "pod_is_ready", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_07(FixtureOc(), ns) if not item.passed}
        self.assertTrue({"07-branches", "07-notebook", "07-merge"}.issubset(failed))

        modified_existing_only = {
            "repository": True,
            "feature_branches": [branch],
            "notebook_candidates": [],
            "merged_candidates": [],
            "clean": True,
        }
        with (
            patch.object(grade, "task07_git_evidence", return_value=modified_existing_only),
            patch.object(grade, "pod_is_ready", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_07(FixtureOc(), ns) if not item.passed}
        self.assertIn("07-notebook", failed)

        unmerged = dict(evidence, merged_candidates=[])
        with (
            patch.object(grade, "task07_git_evidence", return_value=unmerged),
            patch.object(grade, "pod_is_ready", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_07(FixtureOc(), ns) if not item.passed}
        self.assertIn("07-merge", failed)

    def test_task07_probe_rejects_baseline_and_existing_notebook_modification(self) -> None:
        def run(*args: str) -> None:
            subprocess.run(args, check=True, capture_output=True, text=True)

        def probe(repo: Path) -> dict:
            code = grade.TASK07_GIT_PROBE.replace(
                'pathlib.Path("/opt/app-root/src/AI26X-apps")',
                f"pathlib.Path({str(repo)!r})",
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(result.stdout)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "AI26X-apps"
            run("git", "init", "-b", "RHOAI3.3", str(repo))
            run("git", "-C", str(repo), "config", "user.name", "AI267 Test")
            run("git", "-C", str(repo), "config", "user.email", "ai267@example.invalid")
            baseline = repo / "workbench" / "working" / "train_model.ipynb"
            baseline.parent.mkdir(parents=True)
            baseline.write_text('{"cells": []}\n', encoding="utf-8")
            run("git", "-C", str(repo), "add", ".")
            run("git", "-C", str(repo), "commit", "-m", "baseline")
            run(
                "git",
                "-C",
                str(repo),
                "remote",
                "add",
                "origin",
                "https://github.com/RedHatTraining/AI26X-apps.git",
            )
            run(
                "git",
                "-C",
                str(repo),
                "update-ref",
                "refs/remotes/origin/RHOAI3.3",
                "HEAD",
            )

            baseline_evidence = probe(repo)
            self.assertTrue(baseline_evidence["repository"])
            self.assertEqual(baseline_evidence["feature_branches"], [])
            self.assertEqual(baseline_evidence["notebook_candidates"], [])

            run("git", "-C", str(repo), "checkout", "-b", "feature/modify-existing")
            baseline.write_text('{"cells": [{"cell_type": "markdown"}]}\n', encoding="utf-8")
            run("git", "-C", str(repo), "add", str(baseline.relative_to(repo)))
            run("git", "-C", str(repo), "commit", "-m", "modify existing notebook")
            run("git", "-C", str(repo), "checkout", "RHOAI3.3")
            run("git", "-C", str(repo), "merge", "--ff-only", "feature/modify-existing")

            modified_evidence = probe(repo)
            self.assertEqual(modified_evidence["feature_branches"], ["feature/modify-existing"])
            self.assertEqual(modified_evidence["notebook_candidates"], [])
            self.assertEqual(modified_evidence["merged_candidates"], [])

            run("git", "-C", str(repo), "checkout", "-b", "topic/free-name")
            new_notebook = repo / "team" / "new-analysis.ipynb"
            new_notebook.parent.mkdir(parents=True)
            new_notebook.write_text('{"cells": []}\n', encoding="utf-8")
            run("git", "-C", str(repo), "add", str(new_notebook.relative_to(repo)))
            run("git", "-C", str(repo), "commit", "-m", "track new notebook")
            run("git", "-C", str(repo), "checkout", "RHOAI3.3")
            run("git", "-C", str(repo), "merge", "--ff-only", "topic/free-name")

            happy = probe(repo)
            self.assertIn("topic/free-name", happy["feature_branches"])
            self.assertIn(
                {"branch": "topic/free-name", "paths": ["team/new-analysis.ipynb"]},
                happy["notebook_candidates"],
            )
            self.assertIn(
                {"branch": "topic/free-name", "paths": ["team/new-analysis.ipynb"]},
                happy["merged_candidates"],
            )

    def test_task10_happy_fixture_and_wrong_interval_near_miss(self) -> None:
        ns = "dspa-kubeflow"
        oc = FixtureOc()
        oc.add_list(
            "datasciencepipelinesapplication.datasciencepipelinesapplications.opendatahub.io",
            [{"status": {"conditions": [{"type": "Ready", "status": "True"}]}}],
            ns,
        )
        schedule = {
            "metadata": {"name": "tas1-devops-wala-s1"},
            "spec": {
                "enabled": True,
                "pipelineName": "tas1-devops-wala",
                "trigger": {"periodicSchedule": {"intervalSecond": 300}},
            },
        }
        oc.add_list("scheduledworkflow.kubeflow.org", [schedule], ns)
        oc.add_list("cronworkflow.argoproj.io", [], ns)
        oc.add_list(
            "workflow.argoproj.io",
            [
                {
                    "metadata": {
                        "name": "tas1-devops-wala-s1-7cf9",
                        "ownerReferences": [{"name": "tas1-devops-wala-s1"}],
                    },
                    "status": {"phase": "Succeeded"},
                }
            ],
            ns,
        )
        compiled = "pipelineInfo:\n  name: tas1-devops-wala\nsdkVersion: kfp-2.15.2\n"
        with patch.object(grade, "read_text_if_file", return_value=compiled):
            results = grade.grader_10(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)

        broken = copy.deepcopy(oc)
        broken.lists[("scheduledworkflow.kubeflow.org", ns)][0]["spec"]["trigger"]["periodicSchedule"][
            "intervalSecond"
        ] = 600
        with patch.object(grade, "read_text_if_file", return_value=compiled):
            failed = {item.check_id for item in grade.grader_10(broken, ns) if not item.passed}
        self.assertIn("10-schedule", failed)

        wrong_pipeline = copy.deepcopy(oc)
        wrong_pipeline.lists[("scheduledworkflow.kubeflow.org", ns)][0]["spec"][
            "pipelineName"
        ] = "unrelated-pipeline"
        with patch.object(grade, "read_text_if_file", return_value=compiled):
            failed = {
                item.check_id for item in grade.grader_10(wrong_pipeline, ns) if not item.passed
            }
        self.assertIn("10-import", failed)

        forged_run = copy.deepcopy(oc)
        forged_run.lists[("workflow.argoproj.io", ns)][0]["metadata"].pop("ownerReferences")
        with patch.object(grade, "read_text_if_file", return_value=compiled):
            failed = {
                item.check_id for item in grade.grader_10(forged_run, ns) if not item.passed
            }
        self.assertIn("10-run", failed)

    def test_task11_happy_fixture_and_failed_stage_near_miss(self) -> None:
        ns = "dspa-intro"
        oc = FixtureOc()
        oc.add(
            "secret",
            "my-s3-connection",
            {
                "metadata": {
                    "annotations": {"opendatahub.io/connection-type-protocol": "s3"}
                },
                "data": {
                    "AWS_ACCESS_KEY_ID": encoded("minio"),
                    "AWS_SECRET_ACCESS_KEY": encoded("minio123"),
                    "AWS_S3_ENDPOINT": encoded(
                        "https://minio-api-minio.apps.lab.example.com"
                    ),
                    "AWS_DEFAULT_REGION": encoded("us-east-1"),
                    "AWS_S3_BUCKET": encoded("saved-models"),
                },
            },
            ns,
        )
        oc.add_list(
            "datasciencepipelinesapplication.datasciencepipelinesapplications.opendatahub.io",
            [
                {
                    "spec": {
                        "objectStorage": {
                            "externalStorage": {
                                "bucket": "saved-models",
                                "s3CredentialsSecret": {"secretName": "my-s3-connection"},
                            }
                        }
                    },
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                }
            ],
            ns,
        )
        pod_names = [
            "ds-pipeline-dspa-abc",
            "ds-pipeline-persistenceagent-abc",
            "ds-pipeline-scheduledworkflow-abc",
        ]
        oc.add_list(
            "pod",
            [
                {
                    "metadata": {"name": name},
                    "status": {"phase": "Running", "containerStatuses": [{"ready": True}]},
                }
                for name in pod_names
            ],
            ns,
        )
        workflow = {
            "metadata": {"annotations": {"pipelines.kubeflow.org/run_name": "carido-training-r1"}},
            "status": {
                "phase": "Succeeded",
                "nodes": {
                    name: {"displayName": name, "phase": "Succeeded"}
                    for name in ("generate-data", "preprocess-data", "train-model", "save-model")
                },
            },
        }
        oc.add_list("workflow.argoproj.io", [workflow], ns)
        compiled = (
            "pipelineInfo:\n  name: carido-training-pipeline\n"
            "root:\n"
            "  dag:\n"
            "    tasks:\n"
            "      generate-data:\n"
            "        taskInfo:\n          name: generate-data\n"
            "      preprocess-data:\n"
            "        inputs:\n"
            "          artifacts:\n"
            "            raw-data:\n"
            "              taskOutputArtifact:\n"
            "                producerTask: generate-data\n"
            "        taskInfo:\n          name: preprocess-data\n"
            "      train-model:\n"
            "        dependentTasks:\n        - preprocess-data\n"
            "        taskInfo:\n          name: train-model\n"
            "      save-model:\n"
            "        inputs:\n"
            "          artifacts:\n"
            "            model:\n"
            "              taskOutputArtifact:\n"
            "                producerTask: train-model\n"
            "        taskInfo:\n          name: save-model\n"
            "sdkVersion: kfp-2.15.2\n"
        )
        with (
            patch.object(grade, "read_text_if_file", return_value=compiled),
            patch.object(grade, "s3_fixture_object_exists", return_value=True) as s3_object,
        ):
            results = grade.grader_11(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)
        s3_object.assert_called_once_with("saved-models", "carido-model.joblib")

        broken = copy.deepcopy(oc)
        broken.lists[("workflow.argoproj.io", ns)][0]["status"]["nodes"]["save-model"]["phase"] = "Failed"
        with (
            patch.object(grade, "read_text_if_file", return_value=compiled),
            patch.object(grade, "s3_fixture_object_exists", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_11(broken, ns) if not item.passed}
        self.assertIn("11-run", failed)

        with (
            patch.object(grade, "read_text_if_file", return_value=compiled),
            patch.object(grade, "s3_fixture_object_exists", return_value=False),
        ):
            failed = {item.check_id for item in grade.grader_11(oc, ns) if not item.passed}
        self.assertIn("11-artifact", failed)

        independent = compiled.replace(
            "                producerTask: generate-data\n", ""
        )
        with (
            patch.object(grade, "read_text_if_file", return_value=independent),
            patch.object(grade, "s3_fixture_object_exists", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_11(oc, ns) if not item.passed}
        self.assertIn("11-compile", failed)

        reverse_order = compiled.replace(
            "                producerTask: generate-data\n",
            "                producerTask: train-model\n",
        )
        with (
            patch.object(grade, "read_text_if_file", return_value=reverse_order),
            patch.object(grade, "s3_fixture_object_exists", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_11(oc, ns) if not item.passed}
        self.assertIn("11-compile", failed)

    def test_task12_happy_fixture_and_disconnected_graph_near_miss(self) -> None:
        ns = "dspa-elyra"
        oc = FixtureOc()
        oc.add_list(
            "datasciencepipelinesapplication.datasciencepipelinesapplications.opendatahub.io",
            [{"status": {"conditions": [{"type": "Ready", "status": "True"}]}}],
            ns,
        )
        oc.add(
            "notebook.kubeflow.org",
            "pipelines-elyra-wb",
            notebook(
                "pipelines-elyra-wb",
                "registry/generic-data-science:latest",
                annotations={
                    "opendatahub.io/image-display-name": "Jupyter | Data Science | CPU | Python 3.12",
                    "opendatahub.io/connections": '["s3-minio"]',
                },
                claim="pipelines-elyra-wb-storage",
            ),
            ns,
        )
        oc.add(
            "pvc",
            "pipelines-elyra-wb-storage",
            {
                "spec": {"resources": {"requests": {"storage": "10Gi"}}},
                "status": {"phase": "Bound"},
            },
            ns,
        )

        def node(node_id: str, script: str, output: str, target: str | None = None) -> dict:
            return {
                "id": node_id,
                "app_data": {"component_parameters": {"filename": script, "outputs": [output]}},
                "inputs": [],
                "outputs": [{"links": [] if target is None else [{"node_id": target}]}],
            }

        document = {
            "pipelines": [
                {
                    "nodes": [
                        node("ingest", "data_ingestion.py", "data.csv", "clean"),
                        node("clean", "data_preprocessing.py", "clean-data.csv", "forecast"),
                        node("forecast", "data_training_and_forecasting.py", "forecast-data.csv"),
                    ],
                    "app_data": {
                        "properties": {
                            "runtime": "Pipelines",
                            "pipeline_defaults": {
                                "runtime_image": grade.ELYRA_RUNTIME_IMAGE,
                                "kubernetes_secrets": [
                                    {
                                        "env_var": key,
                                        "name": "aws-connection-s3-minio",
                                        "key": key,
                                    }
                                    for key in (
                                        "AWS_ACCESS_KEY_ID",
                                        "AWS_SECRET_ACCESS_KEY",
                                        "AWS_S3_ENDPOINT",
                                        "AWS_S3_BUCKET",
                                    )
                                ],
                            },
                        }
                    },
                }
            ]
        }
        oc.add_list(
            "workflow.argoproj.io",
            [{"metadata": {"name": "issues-prediction-7cf9"}, "status": {"phase": "Succeeded"}}],
            ns,
        )
        with (
            patch.object(grade, "exec_stdout", return_value=json.dumps(document)),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "elyra_runtime_image_metadata_ok", return_value=True),
            patch.object(grade, "s3_prefix_has", return_value=True),
        ):
            results = grade.grader_12(oc, ns)
        self.assertTrue(all(item.passed for item in results), results)

        broken = copy.deepcopy(document)
        broken["pipelines"][0]["nodes"][0]["outputs"][0]["links"] = []
        with (
            patch.object(grade, "exec_stdout", return_value=json.dumps(broken)),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "elyra_runtime_image_metadata_ok", return_value=True),
            patch.object(grade, "s3_prefix_has", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_12(oc, ns) if not item.passed}
        self.assertIn("12-pipeline", failed)

        wrong_mapping = copy.deepcopy(document)
        wrong_mapping["pipelines"][0]["app_data"]["properties"]["pipeline_defaults"][
            "kubernetes_secrets"
        ][0]["name"] = "s3-minio"
        with (
            patch.object(grade, "exec_stdout", return_value=json.dumps(wrong_mapping)),
            patch.object(grade, "pod_is_ready", return_value=True),
            patch.object(grade, "git_check", return_value=True),
            patch.object(grade, "elyra_runtime_image_metadata_ok", return_value=True),
            patch.object(grade, "s3_prefix_has", return_value=True),
        ):
            failed = {item.check_id for item in grade.grader_12(oc, ns) if not item.passed}
        self.assertIn("12-pipeline", failed)


class HelperRegressionTests(unittest.TestCase):
    def test_stopped_workbench_verifier_mounts_read_only_and_always_deletes(self) -> None:
        class Result:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        class JobOc:
            def __init__(self, delete_rc: int = 0, already_gone: bool = False) -> None:
                self.manifest: dict = {}
                self.calls: list[tuple[str, ...]] = []
                self.delete_rc = delete_rc
                self.already_gone = already_gone

            def run_input(self, input_text: str, *args: str, timeout: int = 30):
                self.manifest = json.loads(input_text)
                self.calls.append(args)
                return Result(stdout="malformed-but-ignored")

            def run(self, *args: str, timeout: int = 30):
                self.calls.append(args)
                if args[0] == "logs":
                    return Result(stdout='{"repository": true, "branch": true, "file": true}\n')
                if args[0] == "get":
                    if self.already_gone:
                        return Result(returncode=1, stderr="Error from server (NotFound): jobs not found")
                    return Result(
                        stdout=json.dumps(
                            {
                                "metadata": {
                                    "labels": {"ai267.practice/created-by": "task-05-grader"}
                                }
                            }
                        )
                    )
                if args[0] == "delete":
                    return Result(returncode=self.delete_rc)
                return Result()

        wb = notebook("model-training", "registry/pytorch:latest", claim="model-training-pvc")
        container = wb["spec"]["template"]["spec"]["containers"][0]
        container["volumeMounts"] = [{"name": "workspace", "mountPath": "/opt/app-root/src"}]
        wb["spec"]["template"]["spec"].update(
            {
                "serviceAccountName": "notebook-privileged",
                "imagePullSecrets": [{"name": "redhat-registry-pull"}],
            }
        )

        oc = JobOc()
        self.assertEqual(
            grade.stopped_notebook_repo_checks(oc, "workbench-working", wb),
            (True, True, True),
        )
        job_spec = oc.manifest["spec"]["template"]["spec"]
        self.assertFalse(job_spec["automountServiceAccountToken"])
        self.assertNotIn("serviceAccountName", job_spec)
        self.assertEqual(
            job_spec["imagePullSecrets"], [{"name": "redhat-registry-pull"}]
        )
        self.assertTrue(job_spec["containers"][0]["volumeMounts"][0]["readOnly"])
        self.assertTrue(job_spec["volumes"][0]["persistentVolumeClaim"]["readOnly"])
        job_name = oc.manifest["metadata"]["name"]
        self.assertTrue(job_name.startswith("ai267-grade-05-"))
        self.assertIn(
            ("delete", "job", job_name, "-n", "workbench-working", "--wait=true", "--timeout=60s"),
            oc.calls,
        )

        # Execute the exact verifier embedded in the Job manifest. A mocked Job
        # log alone cannot catch invalid subprocess.run arguments in that code.
        verify_code = job_spec["containers"][0]["command"][2]
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "AI26X-apps"
            (repo / "workbench" / "working").mkdir(parents=True)
            (repo / "workbench" / "working" / "train_model.ipynb").write_text(
                "{}", encoding="utf-8"
            )
            subprocess.run(
                ["git", "init", "-b", "RHOAI3.3", str(repo)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "remote",
                    "add",
                    "origin",
                    "https://github.com/RedHatTraining/AI26X-apps.git",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            executable_code = verify_code.replace(
                'pathlib.Path("/workspace/AI26X-apps")',
                f"pathlib.Path({str(repo)!r})",
            )
            executed = subprocess.run(
                [sys.executable, "-c", executable_code],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            evidence = json.loads(executed.stdout.strip())
            self.assertEqual(
                evidence,
                {"repository": True, "branch": True, "file": True},
            )

        already_gone = JobOc(already_gone=True)
        self.assertEqual(
            grade.stopped_notebook_repo_checks(already_gone, "workbench-working", wb),
            (True, True, True),
        )
        self.assertFalse(any(call[0] == "delete" for call in already_gone.calls))

        cleanup_failure = JobOc(delete_rc=1)
        self.assertEqual(
            grade.stopped_notebook_repo_checks(cleanup_failure, "workbench-working", wb),
            (False, False, False),
        )

    def test_connection_annotation_json_and_exact_s3_values(self) -> None:
        ns = "workbench-connections"
        wb = notebook(
            "wb",
            "image",
            annotations={"opendatahub.io/connections": '["minio"]'},
        )
        self.assertTrue(grade.notebook_has_connection(wb, ns, "minio"))
        self.assertFalse(grade.notebook_has_connection(wb, ns, "mini"))

        prefixed_annotation = notebook(
            "wb",
            "image",
            annotations={
                "opendatahub.io/connections": (
                    '["workbench-connections/aws-connection-minio"]'
                )
            },
        )
        self.assertTrue(
            grade.notebook_has_connection(prefixed_annotation, ns, "minio")
        )
        self.assertFalse(
            grade.notebook_has_connection(prefixed_annotation, ns, "mini")
        )

        prefixed_env = notebook(
            "wb",
            "image",
            env_from=[{"secretRef": {"name": "aws-connection-minio"}}],
        )
        self.assertTrue(grade.notebook_has_connection(prefixed_env, ns, "minio"))
        self.assertFalse(grade.notebook_has_connection(prefixed_env, ns, "mini"))

        secret = {
            "metadata": {"annotations": {"opendatahub.io/connection-type-protocol": "s3"}},
            "data": {
                "AWS_ACCESS_KEY_ID": encoded("minio"),
                "AWS_SECRET_ACCESS_KEY": encoded("minio123"),
                "AWS_S3_ENDPOINT": encoded("https://minio-api-minio.apps.lab.example.com/"),
                "AWS_DEFAULT_REGION": encoded("us-east-1"),
                "AWS_S3_BUCKET": encoded("workbench-connections-bucket"),
            },
        }
        expected = dict(
            access_key="minio",
            secret_key="minio123",
            endpoint="https://minio-api-minio.apps.lab.example.com",
            region="us-east-1",
            bucket="workbench-connections-bucket",
        )
        self.assertTrue(grade.s3_connection_matches(secret, **expected))
        wrong = copy.deepcopy(secret)
        wrong["data"]["AWS_S3_ENDPOINT"] = encoded("https://other.example.com")
        self.assertFalse(grade.s3_connection_matches(wrong, **expected))

    def test_elyra_graph_happy_and_near_misses(self) -> None:
        def node(node_id: str, script: str, output: str, target: str | None = None) -> dict:
            links = [] if target is None else [{"node_id": target}]
            return {
                "id": node_id,
                "app_data": {"component_parameters": {"filename": script, "outputs": [output]}},
                "inputs": [],
                "outputs": [{"links": links}],
            }

        document = {
            "pipelines": [
                {
                    "nodes": [
                        node("ingest", "data_ingestion.py", "data.csv", "clean"),
                        node("clean", "data_preprocessing.py", "clean-data.csv", "forecast"),
                        node("forecast", "data_training_and_forecasting.py", "forecast-data.csv"),
                    ],
                    "app_data": {"properties": {"runtime": "Pipelines"}},
                }
            ]
        }
        self.assertEqual(grade.elyra_pipeline_checks(json.dumps(document)), (True, True))

        # Elyra examples may persist a repository-relative filename and put the
        # edge reference on the downstream input port as node_id_ref.
        official_shape = copy.deepcopy(document)
        official_nodes = official_shape["pipelines"][0]["nodes"]
        for item in official_nodes:
            filename = item["app_data"]["component_parameters"]["filename"]
            item["app_data"]["component_parameters"]["filename"] = (
                f"AI26X-apps/dspa/elyra/{filename}"
            )
            item["outputs"] = [{"id": "outPort"}]
            item["inputs"] = [{"id": "inPort"}]
        official_nodes[1]["inputs"][0]["links"] = [
            {"node_id_ref": "ingest", "port_id_ref": "outPort"}
        ]
        official_nodes[2]["inputs"][0]["links"] = [
            {"node_id_ref": "clean", "port_id_ref": "outPort"}
        ]
        self.assertEqual(
            grade.elyra_pipeline_checks(json.dumps(official_shape)),
            (True, True),
        )

        disconnected = copy.deepcopy(document)
        disconnected["pipelines"][0]["nodes"][1]["outputs"][0]["links"] = []
        self.assertEqual(grade.elyra_pipeline_checks(json.dumps(disconnected)), (False, True))

        wrong_output = copy.deepcopy(document)
        wrong_output["pipelines"][0]["nodes"][1]["app_data"]["component_parameters"]["outputs"] = [
            "wrong.csv"
        ]
        self.assertEqual(grade.elyra_pipeline_checks(json.dumps(wrong_output)), (True, False))

        substring_output = copy.deepcopy(document)
        substring_output["pipelines"][0]["nodes"][0]["app_data"]["component_parameters"][
            "outputs"
        ] = ["not-data.csv"]
        self.assertEqual(
            grade.elyra_pipeline_checks(json.dumps(substring_output)),
            (True, False),
        )

        substring_filename = copy.deepcopy(document)
        substring_filename["pipelines"][0]["nodes"][0]["app_data"][
            "component_parameters"
        ]["filename"] = "backup-data_ingestion.py"
        self.assertEqual(
            grade.elyra_pipeline_checks(json.dumps(substring_filename)),
            (False, False),
        )

        defaults = document["pipelines"][0]["app_data"]["properties"]["pipeline_defaults"] = {
            "runtime_image": grade.ELYRA_RUNTIME_IMAGE,
            "kubernetes_secrets": [
                {"env_var": key, "name": "aws-connection-s3-minio", "key": key}
                for key in (
                    "AWS_ACCESS_KEY_ID",
                    "AWS_SECRET_ACCESS_KEY",
                    "AWS_S3_ENDPOINT",
                    "AWS_S3_BUCKET",
                )
            ],
        }
        self.assertTrue(grade.elyra_pipeline_settings_ok(json.dumps(document)))
        defaults["runtime_image"] = "quay.io/redhattraining/forecast-pipeline-runtime:1.0"
        self.assertFalse(grade.elyra_pipeline_settings_ok(json.dumps(document)))
        defaults["runtime_image"] = grade.ELYRA_RUNTIME_IMAGE
        defaults["kubernetes_secrets"].append(
            {"env_var": "EXTRA", "name": "aws-connection-s3-minio", "key": "EXTRA"}
        )
        self.assertFalse(grade.elyra_pipeline_settings_ok(json.dumps(document)))

    def test_elyra_runtime_metadata_uses_official_33_image(self) -> None:
        with patch.object(grade, "exec_ok", return_value=True) as exec_ok:
            self.assertTrue(
                grade.elyra_runtime_image_metadata_ok(
                    FixtureOc(), "dspa-elyra", "pipelines-elyra-wb"
                )
            )
        command = exec_ok.call_args.args[3]
        self.assertEqual(command[:2], ["python3", "-c"])
        self.assertIn(grade.ELYRA_RUNTIME_DISPLAY_NAME, command[2])
        self.assertIn(grade.ELYRA_RUNTIME_IMAGE, command[2])
        self.assertNotIn("quay.io/redhattraining/forecast-pipeline-runtime:1.0", command[2])

    def test_workflow_name_uses_boundaries(self) -> None:
        exact = {"metadata": {"annotations": {"pipelines.kubeflow.org/run_name": "issues_prediction"}}}
        generated = {"metadata": {"name": "issues-prediction-7cf9"}}
        near_miss = {"metadata": {"name": "not-issues-prediction-copy"}}
        self.assertTrue(grade.workflow_named(exact, "issues_prediction"))
        self.assertTrue(grade.workflow_named(generated, "issues_prediction"))
        self.assertFalse(grade.workflow_named(near_miss, "issues_prediction"))

    def test_compiled_kfp_ir_requires_exact_sdk(self) -> None:
        valid = "pipelineInfo:\n  name: tas1-devops-wala\nsdkVersion: kfp-2.15.2\n"
        old_sdk = valid.replace("2.15.2", "2.14.3")
        self.assertTrue(grade.compiled_kfp_ir_matches(valid, "tas1-devops-wala", "2.15.2"))
        self.assertFalse(grade.compiled_kfp_ir_matches(old_sdk, "tas1-devops-wala", "2.15.2"))

    def test_kfp_dependency_parser_has_no_pyyaml_runtime_requirement(self) -> None:
        compiled = (
            "root:\n"
            "  dag:\n"
            "    tasks:\n"
            "      generate-data:\n"
            "        taskInfo:\n          name: generate-data\n"
            "      preprocess-data:\n"
            "        inputs:\n"
            "          artifacts:\n"
            "            raw-data:\n"
            "              taskOutputArtifact:\n"
            "                producerTask: generate-data\n"
            "      train-model:\n"
            "        dependentTasks:\n        - preprocess-data\n"
            "      save-model:\n"
            "        dependentTasks: [train-model]\n"
        )
        self.assertEqual(
            grade._kfp_root_task_dependencies_text(compiled),
            {
                "generate-data": set(),
                "preprocess-data": {"generate-data"},
                "train-model": {"preprocess-data"},
                "save-model": {"train-model"},
            },
        )
        self.assertTrue(
            grade.compiled_pipeline_has_ordered_chain(
                compiled,
                ["generate-data", "preprocess-data", "train-model", "save-model"],
            )
        )

    def test_s3_fixture_uses_shared_helper_path(self) -> None:
        expected = ROOT / "tasks" / "common" / "s3_fixture.py"
        self.assertTrue(expected.is_file(), expected)
        with patch.object(
            grade.runpy,
            "run_path",
            return_value={"signed_request": lambda method, bucket, key: (200, b"model")},
        ) as run_path:
            self.assertTrue(grade.s3_fixture_object_exists("saved-models", "artifact/model"))
        run_path.assert_called_once_with(str(expected), run_name="ai267_s3_fixture")

        with patch.object(
            grade.runpy,
            "run_path",
            return_value={"signed_request": lambda method, bucket, key: (200, b"")},
        ):
            self.assertFalse(grade.s3_fixture_object_exists("saved-models", "artifact/model"))

    def test_unauthenticated_inference_uses_documented_five_feature_payload(self) -> None:
        class Response:
            def __init__(self, body: dict, status: int = 200) -> None:
                self.body = json.dumps(body).encode()
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self) -> bytes:
                return self.body

        metadata = {
            "inputs": [{"name": "float_input", "datatype": "FP32", "shape": [-1, 5]}]
        }
        with patch.object(
            grade.urllib.request,
            "urlopen",
            side_effect=[Response(metadata), Response({"outputs": [{"name": "label"}]})],
        ) as urlopen:
            self.assertTrue(
                grade.unauthenticated_v2_inference_ok(
                    "diabetes.apps.lab.example.com",
                    "diabetes",
                )
            )
        metadata_request = urlopen.call_args_list[0].args[0]
        inference_request = urlopen.call_args_list[1].args[0]
        self.assertTrue(metadata_request.full_url.endswith("/v2/models/diabetes"))
        body = json.loads(inference_request.data)
        self.assertEqual(body["inputs"][0]["shape"], [1, 5])
        self.assertEqual(body["inputs"][0]["data"], [[0.2, -0.1, 0.5, 1.0, -0.4]])
        self.assertNotIn("Authorization", inference_request.headers)

        wrong_metadata = {
            "inputs": [{"name": "float_input", "datatype": "FP32", "shape": [-1, 8]}]
        }
        with patch.object(grade.urllib.request, "urlopen", return_value=Response(wrong_metadata)):
            self.assertFalse(
                grade.unauthenticated_v2_inference_ok(
                    "diabetes.apps.lab.example.com",
                    "diabetes",
                )
            )


if __name__ == "__main__":
    unittest.main()
