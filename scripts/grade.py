#!/usr/bin/env python3
"""EX267 v3.3 practice-lab resource grader.

The grader reads Kubernetes/OpenShift resources only. It never prints Secret data.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import subprocess
import sys
from typing import Any, Callable


TASKS = {
    "01": ("ex267-fraud", 21, "사용자·프로젝트·S3"),
    "02": ("ex267-t02-workbench", 30, "Workbench·이미지·Git·S3"),
    "03": ("ex267-t03-pipeline", 36, "KFP·Elyra Pipeline·예약 실행"),
    "04": ("ex267-t04-serving", 36, "OpenVINO·Custom Runtime·인증"),
    "05": ("ex267-t05-vllm", 30, "vLLM·GPU 배치 진단"),
    "06": ("ex267-t06-registry", 30, "Model Registry·계보"),
    "07": ("ex267-t07-monitoring", 30, "TrustyAI·플랫폼 모니터링"),
    "08": ("ex267-t08-evaluation", 24, "LLM 최적화·LMEval"),
    "09": ("ex267-t09-rag", 30, "Guardrailed RAG"),
    "10": ("ex267-t10-evidence", 24, "재현·증적·롤백"),
}

SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
PINNED_IMAGE = re.compile(r"@sha256:[0-9a-f]{64}$")
TODO_VALUES = {"", "todo", "replace_me", "replace-me", "pending", "unknown", "n/a"}
RAG_VERIFIER_SHA256 = "748680af31b40caa35d09bd660034a660e48602be19097904200e429b464edcf"
RAG_VERIFIER_IMAGE = "registry.access.redhat.com/ubi9/python-312:9.6"


@dataclass
class Result:
    check_id: str
    description: str
    points: int
    passed: bool
    detail: str


class Oc:
    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["oc", *args], text=True, capture_output=True, check=False
        )

    def get(self, kind: str, name: str, namespace: str | None = None) -> dict[str, Any] | None:
        args = ["get", kind, name]
        if namespace:
            args += ["-n", namespace]
        args += ["-o", "json"]
        result = self.run(*args)
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    def list(self, kind: str, namespace: str, selector: str | None = None) -> list[dict[str, Any]]:
        args = ["get", kind, "-n", namespace]
        if selector:
            args += ["-l", selector]
        args += ["-o", "json"]
        result = self.run(*args)
        if result.returncode != 0:
            return []
        try:
            return json.loads(result.stdout).get("items", [])
        except json.JSONDecodeError:
            return []

    def list_all(self, kind: str) -> list[dict[str, Any]]:
        result = self.run("get", kind, "-A", "-o", "json")
        if result.returncode != 0:
            return []
        try:
            return json.loads(result.stdout).get("items", [])
        except json.JSONDecodeError:
            return []

    def raw_json(self, path: str) -> dict[str, Any] | None:
        result = self.run("get", "--raw", path)
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None


def dig(value: Any, *path: Any, default: Any = None) -> Any:
    current = value
    for key in path:
        try:
            current = current[key]
        except (KeyError, IndexError, TypeError):
            return default
    return current


def non_todo(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text.lower() not in TODO_VALUES and "<" not in text


def is_sha(value: Any) -> bool:
    return bool(SHA256.fullmatch(str(value or "").strip().lower()))


def is_git_sha(value: Any) -> bool:
    return bool(GIT_SHA.fullmatch(str(value or "").strip().lower()))


def cm_data(oc: Oc, name: str, namespace: str) -> dict[str, str]:
    return dig(oc.get("configmap", name, namespace), "data", default={}) or {}


def has_values(data: dict[str, str], keys: list[str]) -> bool:
    return all(non_todo(data.get(key)) for key in keys)


def condition_true(resource: dict[str, Any] | None, condition_type: str = "Ready") -> bool:
    for condition in dig(resource, "status", "conditions", default=[]) or []:
        if condition.get("type") == condition_type and str(condition.get("status")).lower() == "true":
            return True
    return False


def completed_job(resource: dict[str, Any] | None) -> bool:
    return condition_true(resource, "Complete") or int(dig(resource, "status", "succeeded", default=0) or 0) > 0


def secret_values_are_real(secret: dict[str, Any] | None, keys: list[str]) -> bool:
    if not secret:
        return False
    data = secret.get("data", {})
    if not all(key in data for key in keys):
        return False
    for key in keys:
        try:
            decoded = base64.b64decode(data[key]).decode("utf-8", errors="ignore")
        except Exception:
            return False
        if not non_todo(decoded):
            return False
    return True


def secret_data_matches(
    actual: dict[str, Any] | None,
    expected: dict[str, Any] | None,
    keys: list[str],
) -> bool:
    """Compare encoded Secret values without decoding or printing credentials."""
    if not actual or not expected:
        return False
    actual_data = actual.get("data", {}) or {}
    expected_data = expected.get("data", {}) or {}
    return all(
        non_todo(actual_data.get(key))
        and actual_data.get(key) == expected_data.get(key)
        for key in keys
    )


def result(check_id: str, description: str, points: int, passed: bool, detail: str) -> Result:
    return Result(check_id, description, points, bool(passed), detail)


def grade_01(oc: Oc, ns: str) -> list[Result]:
    user_group = oc.get("group", "devops-wala")
    admin_group = oc.get("group", "rhoai-exam-admins")
    user_members = set(user_group.get("users", []) if user_group else [])
    admin_members = set(admin_group.get("users", []) if admin_group else [])
    auth = oc.get("auth.services.platform.opendatahub.io", "auth") \
        or oc.get("auth.services.platform.opendatahub.io", "auth", "redhat-ods-applications")
    allowed_groups = set(dig(auth, "spec", "allowedGroups", default=[]) or [])
    admin_groups = set(dig(auth, "spec", "adminGroups", default=[]) or [])
    managed_groups = all(
        dig(group, "metadata", "labels", "ex267.practice/task", default="") == "01"
        for group in (user_group, admin_group) if group
    ) and user_group is not None and admin_group is not None
    r2 = user_members == {"developer", "rajan", "punit"} \
        and admin_members == {"raja", "andrew"} \
        and "devops-wala" in allowed_groups \
        and "rhoai-exam-admins" in admin_groups \
        and "system:authenticated" not in allowed_groups \
        and managed_groups

    namespace = oc.get("namespace", ns)
    labels = dig(namespace, "metadata", "labels", default={}) or {}
    r3 = labels.get("team") == "northstar-risk" and labels.get("environment") == "exam"

    rolebindings = oc.list("rolebinding", ns)
    roles_by_user: dict[str, list[str]] = {}
    for binding in rolebindings:
        subjects = binding.get("subjects", []) or []
        role_name = dig(binding, "roleRef", "name", default="")
        for subject in subjects:
            if subject.get("kind") == "User":
                roles_by_user.setdefault(subject.get("name", ""), []).append(role_name)
    developer_roles = roles_by_user.get("developer1", [])
    r4 = "edit" in developer_roles and not ({"admin", "cluster-admin"} & set(developer_roles))
    r5 = all("admin" in roles_by_user.get(name, []) for name in ("rajan", "punit")) \
        and "edit" in roles_by_user.get("suraj", []) \
        and not any("cluster-admin" in roles_by_user.get(name, []) for name in ("rajan", "punit", "suraj"))

    connection = oc.get("secret", "fraud-s3", ns)
    provided_connection = oc.get("secret", "exam-provided-minio", ns)
    annotation = dig(connection, "metadata", "annotations", "opendatahub.io/connection-type-protocol")
    s3_keys = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT", "AWS_S3_BUCKET"]
    r6 = annotation == "s3" \
        and secret_values_are_real(connection, s3_keys) \
        and secret_data_matches(connection, provided_connection, s3_keys)

    evidence = cm_data(oc, "fraud-s3-evidence", ns)
    r7 = has_values(evidence, ["input_key", "output_key", "input_sha256", "output_sha256", "verified_from_new_process"]) \
        and is_sha(evidence.get("input_sha256")) and is_sha(evidence.get("output_sha256")) \
        and evidence.get("input_key") != evidence.get("output_key") \
        and evidence.get("verified_from_new_process", "").lower() == "true"

    r8 = bool(auth) and allowed_groups == {"devops-wala"} \
        and admin_groups == {"rhoai-exam-admins"}

    return [
        result("01-1", "사용자·관리자 그룹 구성과 Auth 연결", 3, r2, f"users={sorted(user_members)}, admins={sorted(admin_members)}"),
        result("01-2", "프로젝트 팀·환경 라벨", 3, r3, "team=northstar-risk, environment=exam"),
        result("01-3", "developer1 최소 권한 edit RoleBinding", 3, r4, f"roles={developer_roles or ['none']}"),
        result("01-4", "rajan·punit admin, suraj edit 프로젝트 협업 권한", 3, r5, "namespace 범위 RoleBinding"),
        result("01-5", "fraud-s3 protocol·endpoint·bucket·Secret", 3, r6, "Secret 값은 출력하지 않음"),
        result("01-6", "새 프로세스 read/write SHA-256 증적", 3, r7, "fraud-s3-evidence ConfigMap"),
        result("01-7", "Dashboard 접근 allowlist가 지정 두 그룹으로 제한됨", 3, r8, "Auth/auth"),
    ]


def grade_02(oc: Oc, ns: str) -> list[Result]:
    image_stream = oc.get("imagestream", "custom-workbench", ns)
    tags = dig(image_stream, "spec", "tags", default=[]) or []
    image_tag = next((item for item in tags if item.get("name") == "1.0"), {})
    tag_annotations = image_tag.get("annotations", {}) or {}
    dependencies = str(tag_annotations.get("opendatahub.io/notebook-python-dependencies", "")).lower()
    image_labels = dig(image_stream, "metadata", "labels", default={}) or {}
    r1 = image_stream is not None \
        and image_labels.get("opendatahub.io/notebook-image") == "true" \
        and "seaborn" in dependencies and "0.12.2" in dependencies \
        and "python-json-logger" in dependencies and "2.0.7" in dependencies \
        and non_todo(dig(image_tag, "from", "name", default=""))

    notebook = oc.get("notebook", "risk-lab", ns)
    container = dig(notebook, "spec", "template", "spec", "containers", 0, default={}) or {}
    image = container.get("image", "")
    custom_image = cm_data(oc, "custom-image-evidence", ns)
    culler_resource = oc.get("configmap", "notebook-controller-culler-config", "redhat-ods-applications")
    culler = dig(culler_resource, "data", default={}) or {}
    r2 = "custom-workbench" in image.lower() \
        and is_sha(custom_image.get("image_digest")) \
        and custom_image.get("seaborn_version") == "0.12.2" \
        and custom_image.get("python_json_logger_version") == "2.0.7" \
        and custom_image.get("idle_culling_endpoint_verified", "").lower() == "true" \
        and culler.get("ENABLE_CULLING", "").lower() == "true" \
        and culler.get("CULL_IDLE_TIME") == "240" \
        and culler.get("IDLENESS_CHECK_PERIOD") == "1" \
        and dig(culler_resource, "metadata", "labels", "ex267.practice/task", default="") == "02"

    volumes = dig(notebook, "spec", "template", "spec", "volumes", default=[]) or []
    mounts = container.get("volumeMounts", []) or []
    claim_names = [dig(volume, "persistentVolumeClaim", "claimName") for volume in volumes]
    storage_claim = next((name for name in claim_names if name), None)
    pvc = oc.get("pvc", storage_claim, ns) if storage_claim else None
    storage = dig(pvc, "spec", "resources", "requests", "storage", default="")
    mounted = any(mount.get("mountPath") == "/opt/app-root/src" for mount in mounts)
    r3 = storage in {"10Gi", "10240Mi"} and mounted

    resources = container.get("resources", {}) or {}
    requests = resources.get("requests", {}) or {}
    limits = resources.get("limits", {}) or {}
    r4 = requests.get("cpu") in {"1", "1000m"} \
        and requests.get("memory") in {"1Gi", "1024Mi"} \
        and limits.get("cpu") in {"2", "2000m"} \
        and limits.get("memory") in {"2Gi", "2048Mi"}

    medium_small = oc.get("hardwareprofile", "medium-small", ns)
    my_medium = oc.get("hardwareprofile", "my-medium", ns)
    medium_ids = {item.get("identifier"): item for item in (dig(medium_small, "spec", "identifiers", default=[]) or [])}
    my_ids = {item.get("identifier"): item for item in (dig(my_medium, "spec", "identifiers", default=[]) or [])}
    r5 = str(dig(medium_ids, "cpu", "minCount", default="")) == "1" \
        and str(dig(medium_ids, "cpu", "maxCount", default="")) == "2" \
        and str(dig(medium_ids, "memory", "minCount", default="")) == "16Gi" \
        and str(dig(medium_ids, "memory", "maxCount", default="")) == "16Gi" \
        and str(dig(my_ids, "cpu", "minCount", default="")) == "1" \
        and str(dig(my_ids, "cpu", "maxCount", default="")) == "2" \
        and str(dig(my_ids, "memory", "minCount", default="")) == "1Gi" \
        and str(dig(my_ids, "memory", "maxCount", default="")) == "2Gi"

    existing = oc.get("notebook", "git-experiments", ns)
    existing_container = dig(existing, "spec", "template", "spec", "containers", 0, default={}) or {}
    env_configmaps = {
        dig(item, "configMapRef", "name")
        for item in existing_container.get("envFrom", []) or []
        if dig(item, "configMapRef", "name")
    }
    env_cm = oc.get("configmap", "git-experiments-env", ns)
    admin_evidence = cm_data(oc, "workbench-admin-evidence", ns)
    r6 = "cuda" in str(existing_container.get("image", "")).lower() \
        and "git-experiments-env" in env_configmaps \
        and dig(env_cm, "data", "RANDOM_SIZE") == "40" \
        and admin_evidence.get("stopped_after_test", "").lower() == "true"

    git_evidence = cm_data(oc, "git-collaboration-evidence", ns)
    r7 = git_evidence.get("repository") == "https://github.com/RedHatTraining/AI26X-apps" \
        and git_evidence.get("source_branch") == "RHOAI3.3" \
        and git_evidence.get("feature_branch") in {"experiment", "experiment2"} \
        and is_git_sha(git_evidence.get("feature_commit")) \
        and is_git_sha(git_evidence.get("merge_commit")) \
        and is_sha(git_evidence.get("experiment_notebook_sha256")) \
        and git_evidence.get("clean_worktree", "").lower() == "true"

    connection = oc.get("secret", "projects-data-connection", ns)
    connection_annotation = dig(connection, "metadata", "annotations", "opendatahub.io/connection-type-protocol")
    notebook_annotations = dig(notebook, "metadata", "annotations", default={}) or {}
    connection_refs = str(notebook_annotations.get("opendatahub.io/connections", "")) \
        + json.dumps(container.get("envFrom", []), ensure_ascii=False)
    r8 = connection_annotation == "s3" \
        and secret_values_are_real(connection, ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT", "AWS_S3_BUCKET"]) \
        and "projects-data-connection" in connection_refs

    s3_evidence = cm_data(oc, "workbench-s3-evidence", ns)
    r9 = has_values(s3_evidence, ["upload_key", "download_sha256"]) \
        and is_sha(s3_evidence.get("download_sha256")) \
        and s3_evidence.get("verified_from_workbench", "").lower() == "true"

    evidence = cm_data(oc, "workbench-evidence", ns)
    reproducible = has_values(evidence, ["git_revision", "data_version", "seed", "image_digest", "artifact_uri"]) \
        and is_sha(evidence.get("image_digest"))
    try:
        runs = int(evidence.get("tensorboard_runs", "0"))
    except ValueError:
        runs = 0
    r10 = reproducible and runs >= 2 and evidence.get("restart_proof", "").lower() == "true"

    return [
        result("02-1", "custom-workbench:1.0 build·catalog metadata", 3, r1, "seaborn 0.12.2, python-json-logger 2.0.7"),
        result("02-2", "risk-lab custom image 실행·package·culling 검증", 3, r2, image or "Notebook 없음"),
        result("02-3", "10Gi PVC와 /opt/app-root/src mount", 3, r3, f"claim={storage_claim}, size={storage or 'none'}"),
        result("02-4", "My-medium 1/2 CPU·1/2Gi 적용", 3, r4, json.dumps(resources, ensure_ascii=False)),
        result("02-5", "MediumSmall·My-medium HardwareProfile", 3, r5, "legacy size selector의 3.3 대응"),
        result("02-6", "기존 git-experiments를 CUDA·ConfigMap으로 수정 후 중지", 3, r6, "RANDOM_SIZE=40"),
        result("02-7", "Jupyter Git feature branch·commit·merge", 3, r7, "git-collaboration-evidence"),
        result("02-8", "Workbench S3 connection 연결", 3, r8, "projects-data-connection"),
        result("02-9", "Workbench에서 S3 upload·download 검증", 3, r9, "workbench-s3-evidence"),
        result("02-10", "재현 metadata·재시작·TensorBoard 2개 run", 3, r10, f"runs={runs}"),
    ]


def grade_03(oc: Oc, ns: str) -> list[Result]:
    dspa = oc.get("dspa", "dspa", ns)
    r1 = condition_true(dspa) or all(
        str(condition.get("status", "")).lower() == "true"
        for condition in (dig(dspa, "status", "conditions", default=[]) or [])
    ) and bool(dig(dspa, "status", "conditions", default=[]))

    pipeline = oc.get("configmap", "fraud-training-pipeline", ns)
    pipeline_text = "\n".join((pipeline or {}).get("data", {}).values()).lower()
    r2 = all(name in pipeline_text for name in ("validate", "train", "evaluate"))
    sdk_version = dig(pipeline, "metadata", "annotations", "ex267.io/kfp-sdk", default="")
    r3 = bool(re.match(r"^2\.(?:1[4-9]|[2-9][0-9])(?:\.|$)", sdk_version)) and non_todo(pipeline_text)

    evidence = cm_data(oc, "pipeline-evidence", ns)
    r4 = has_values(evidence, ["service_account", "secret_name", "resources_verified"]) \
        and evidence.get("resources_verified", "").lower() == "true"
    r5 = has_values(evidence, ["cache_policy", "retry_policy", "artifact_prefix_pattern"])

    workflows = [workflow for workflow in oc.list("workflow", ns) if dig(workflow, "status", "phase") == "Succeeded"]
    depths = {dig(workflow, "metadata", "labels", "ex267.io/max-depth") for workflow in workflows}
    depths.discard(None)
    r6 = len(workflows) >= 2 and len(depths) >= 2 \
        and has_values(evidence, ["approved_model_uri", "approved_model_sha256"]) \
        and is_sha(evidence.get("approved_model_sha256"))

    scheduled = oc.list("scheduledworkflow", ns) + oc.list("cronworkflow", ns)
    schedule_evidence = cm_data(oc, "schedule-evidence", ns)
    interval = schedule_evidence.get("interval_seconds", "")
    schedule_name = schedule_evidence.get("schedule_name", "")
    scheduled_names = {dig(item, "metadata", "name", default="") for item in scheduled}
    scheduled_succeeded = any(
        dig(workflow, "metadata", "labels", "ex267.io/scheduled-run", default="").lower() == "true"
        for workflow in workflows
    )
    r7 = schedule_evidence.get("pipeline_name") == "tas1-devops-wala" \
        and schedule_name == "tas1-devops-wala-s1" \
        and interval == "300" \
        and schedule_evidence.get("enabled", "").lower() == "true" \
        and non_todo(schedule_evidence.get("observed_run")) \
        and bool(scheduled) \
        and (schedule_name in scheduled_names or any("tas1-devops-wala" in name for name in scheduled_names)) \
        and scheduled_succeeded

    elyra_notebook = oc.get("notebook", "pipelines-elyra-wb", ns)
    elyra_container = dig(elyra_notebook, "spec", "template", "spec", "containers", 0, default={}) or {}
    elyra_volumes = dig(elyra_notebook, "spec", "template", "spec", "volumes", default=[]) or []
    elyra_claim = next(
        (dig(volume, "persistentVolumeClaim", "claimName") for volume in elyra_volumes
         if dig(volume, "persistentVolumeClaim", "claimName")),
        None,
    )
    elyra_pvc = oc.get("pvc", elyra_claim, ns) if elyra_claim else None
    elyra_size = dig(elyra_pvc, "spec", "resources", "requests", "storage", default="")
    elyra = cm_data(oc, "elyra-evidence", ns)
    elyra_image = str(elyra_container.get("image", "")).lower()
    r8 = elyra_notebook is not None \
        and elyra_size in {"10Gi", "10240Mi"} \
        and ("standard" in elyra_image or "datascience" in elyra_image) \
        and elyra.get("pipeline_file") == "issues_prediction.pipeline" \
        and elyra.get("workbench_name") == "pipelines-elyra-wb" \
        and elyra.get("workbench_pvc") == elyra_claim \
        and "forecast-pipeline-runtime" in elyra.get("runtime_image", "") \
        and elyra.get("secret_name") == "aws-connection-fraud-s3" \
        and is_git_sha(elyra.get("git_revision")) \
        and non_todo(elyra.get("workflow_name"))

    elyra_workflow = next(
        (workflow for workflow in workflows
         if dig(workflow, "metadata", "name", default="") == elyra.get("workflow_name")),
        None,
    )
    r9 = elyra_workflow is not None \
        and all(is_sha(elyra.get(key)) for key in (
            "data_csv_sha256", "clean_data_csv_sha256", "forecast_data_csv_sha256"
        )) \
        and len({
            str(elyra.get("data_csv_sha256", "")).removeprefix("sha256:"),
            str(elyra.get("clean_data_csv_sha256", "")).removeprefix("sha256:"),
            str(elyra.get("forecast_data_csv_sha256", "")).removeprefix("sha256:"),
        }) == 3

    return [
        result("03-1", "DSPA Ready", 4, r1, "dspa/dspa"),
        result("03-2", "validate·train·evaluate 독립 컴포넌트", 4, r2, "fraud-training-pipeline ConfigMap"),
        result("03-3", "KFP SDK 2.14.3+ compiled definition", 4, r3, f"kfp={sdk_version or 'missing'}"),
        result("03-4", "ServiceAccount·Secret·resources", 4, r4, "pipeline-evidence ConfigMap"),
        result("03-5", "cache·retry·run prefix 안전성", 4, r5, "pipeline-evidence ConfigMap"),
        result("03-6", "서로 다른 max_depth 두 run과 승인 모델", 4, r6, f"succeeded={len(workflows)}, depths={sorted(depths)}"),
        result("03-7", "tas1-devops-wala 5분 예약과 예약 실행 성공", 4, r7, f"schedules={sorted(scheduled_names)}"),
        result("03-8", "Standard Data Science·10Gi Elyra Workbench와 3-node 설정", 4, r8, f"claim={elyra_claim}, size={elyra_size or 'none'}"),
        result("03-9", "Elyra 실행 성공과 세 출력 파일 SHA-256", 4, r9, elyra.get("workflow_name", "missing")),
    ]


def grade_04(oc: Oc, ns: str) -> list[Result]:
    service = oc.get("inferenceservice", "fraud-v2", ns)
    model = dig(service, "spec", "predictor", "model", default={}) or {}
    uri = model.get("storageUri", "")
    connection_path = dig(service, "metadata", "annotations", "opendatahub.io/connection-path", default="") \
        or dig(model, "storage", "path", default="")
    digest = dig(service, "metadata", "annotations", "ex267.io/model-sha256", default="")
    r1 = ("models/fraud/2" in uri or "models/fraud/2" in connection_path) and is_sha(digest)

    runtime = str(model.get("runtime", "")).lower()
    model_format = str(dig(model, "modelFormat", "name", default="")).lower()
    r2 = ("openvino" in runtime or "ovms" in runtime) \
        and model_format in {"onnx", "openvino_ir", "openvino"}

    resources = model.get("resources", {}) or {}
    requests = resources.get("requests", {}) or {}
    limits = resources.get("limits", {}) or {}
    cpu_ok = requests.get("cpu") in {"1", "1000m"} and limits.get("cpu") in {"1", "1000m"}
    memory_ok = requests.get("memory") in {"2Gi", "2048Mi"} and limits.get("memory") in {"2Gi", "2048Mi"}
    r3 = cpu_ok and memory_ok
    r4 = condition_true(service) and non_todo(dig(service, "status", "url"))

    evidence = cm_data(oc, "serving-evidence", ns)
    normal_http = evidence.get("normal_http", "")
    invalid_http = evidence.get("invalid_shape_http", "")
    r5 = normal_http.startswith("2") and invalid_http.startswith("4") \
        and has_values(evidence, ["response_schema_sha256", "invalid_response_sha256"])
    r6 = evidence.get("recreated", "").lower() == "true" \
        and evidence.get("rollback_verified", "").lower() == "true" \
        and is_sha(evidence.get("rollback_model_sha256"))

    custom_runtime = oc.get("servingruntime", "fraud-custom-runtime", ns)
    runtime_containers = dig(custom_runtime, "spec", "containers", default=[]) or []
    runtime_image = dig(runtime_containers, 0, "image", default="")
    runtime_formats = {
        str(item.get("name", "")).lower()
        for item in (dig(custom_runtime, "spec", "supportedModelFormats", default=[]) or [])
    }
    runtime_protocols = {
        str(item).lower()
        for item in (dig(custom_runtime, "spec", "protocolVersions", default=[]) or [])
    }
    runtime_evidence = cm_data(oc, "custom-runtime-evidence", ns)
    r7 = custom_runtime is not None \
        and bool(PINNED_IMAGE.search(runtime_image)) \
        and "sklearn" in runtime_formats \
        and "v2" in runtime_protocols \
        and runtime_evidence.get("runtime_name") == "fraud-custom-runtime" \
        and is_sha(runtime_evidence.get("runtime_image_digest")) \
        and runtime_evidence.get("supported_format", "").lower() == "sklearn" \
        and runtime_evidence.get("validation_http", "").startswith("2")

    mode = cm_data(oc, "serving-mode-evidence", ns)
    route = oc.get("route", "fraud-v2", ns)
    route_host = dig(route, "spec", "host", default="")
    deployment_mode = dig(service, "metadata", "annotations", "serving.kserve.io/deploymentMode", default="")
    r8 = mode.get("legacy_multimodel_status") == "mapped-to-rhoai-3.3-rawdeployment" \
        and mode.get("current_deployment_mode") == "RawDeployment" \
        and deployment_mode == "RawDeployment" \
        and route is not None \
        and mode.get("external_route") == route_host

    service_account = oc.get("serviceaccount", "infer-serviceaccount", ns)
    token_secret_name = mode.get("token_secret", "")
    token_secret = oc.get("secret", token_secret_name, ns) if non_todo(token_secret_name) else None
    token_secret_sa = dig(token_secret, "metadata", "annotations", "kubernetes.io/service-account.name", default="")
    token_secret_type = dig(token_secret, "type", default="")
    r9 = service_account is not None \
        and mode.get("token_service_account") == "infer-serviceaccount" \
        and token_secret_type == "kubernetes.io/service-account-token" \
        and token_secret_sa == "infer-serviceaccount" \
        and mode.get("authenticated_http", "").startswith("2") \
        and mode.get("unauthenticated_http", "") in {"401", "403"} \
        and mode.get("public_http", "").startswith("2")

    return [
        result("04-1", "models/fraud/2 immutable artifact", 4, r1, f"storage={uri or connection_path or 'missing'}"),
        result("04-2", "OpenVINO runtime·model format", 4, r2, f"runtime={runtime}, format={model_format}"),
        result("04-3", "1 CPU·2Gi request/limit", 4, r3, json.dumps(resources, ensure_ascii=False)),
        result("04-4", "InferenceService Ready·URL", 4, r4, "fraud-v2"),
        result("04-5", "V2 정상·invalid shape 응답", 4, r5, f"normal={normal_http or 'none'}, invalid={invalid_http or 'none'}"),
        result("04-6", "재생성·rollback 재검증", 4, r6, "serving-evidence ConfigMap"),
        result("04-7", "고정 digest Custom ServingRuntime·sklearn·V2", 4, r7, runtime_image or "runtime missing"),
        result("04-8", "2.13 Multi-model 요구를 3.3 RawDeployment·외부 Route로 검증", 4, r8, route_host or "route missing"),
        result("04-9", "infer-serviceaccount 토큰 인증과 무인증 전환 호출", 4, r9, "Secret 값은 출력하지 않음"),
    ]


def workload_template(oc: Oc, ns: str) -> tuple[dict[str, Any], str]:
    deployment = oc.get("deployment", "support-llm", ns)
    if deployment:
        return dig(deployment, "spec", "template", "spec", default={}) or {}, "deployment/support-llm"
    pods = oc.list("pod", ns, "app=support-llm") or oc.list("pod", ns, "serving.kserve.io/inferenceservice=support-llm")
    if pods:
        return pods[0].get("spec", {}) or {}, "pod/" + dig(pods[0], "metadata", "name", default="support-llm")
    return {}, "missing"


def grade_05(oc: Oc, ns: str) -> list[Result]:
    evidence = cm_data(oc, "vllm-evidence", ns)
    r1 = has_values(evidence, ["pending_event", "root_cause", "quota_checked", "volume_topology_checked"])

    template, workload = workload_template(oc, ns)
    selector = template.get("nodeSelector", {}) or {}
    tolerations = template.get("tolerations", []) or []
    r2 = selector.get("accelerator") == "nvidia-a10" and any(
        item.get("key") == "nvidia.com/gpu" and item.get("value") == "present" and item.get("effect") == "NoSchedule"
        for item in tolerations
    )

    containers = template.get("containers", []) or []
    container = containers[0] if containers else {}
    resources = container.get("resources", {}) or {}
    gpu = (resources.get("limits", {}) or {}).get("nvidia.com/gpu")
    r3 = str(gpu) == "1" and non_todo((resources.get("requests", {}) or {}).get("cpu")) \
        and non_todo((resources.get("requests", {}) or {}).get("memory"))

    image = container.get("image", "")
    command_line = " ".join(str(item) for item in [
        *container.get("command", []), *container.get("args", [])
    ]).lower()
    deployment = oc.get("deployment", "support-llm", ns)
    ready_pods = [
        pod for pod in oc.list("pod", ns, "app=support-llm")
        if condition_true(pod)
    ]
    workload_ready = deployment_ready(deployment) or bool(ready_pods)
    r4 = workload_ready and ("vllm" in image.lower() or "vllm" in command_line) \
        and bool(PINNED_IMAGE.search(image)) and has_values(evidence, ["model_revision", "stream_http", "stream_transcript_sha256"]) \
        and evidence.get("stream_http", "").startswith("2")
    r5 = has_values(evidence, ["concurrency", "p95_latency_ms", "tokens_per_second", "gpu_memory_mib", "gpu_utilization_pct", "queue_depth", "error_rate"])

    return [
        result("05-1", "Pending event 기반 근본 원인", 6, r1, "vllm-evidence ConfigMap"),
        result("05-2", "A10 selector·정확한 toleration", 6, r2, workload),
        result("05-3", "GPU 1개·CPU·memory request", 6, r3, json.dumps(resources, ensure_ascii=False)),
        result("05-4", "Ready vLLM·고정 image/model revision·streaming", 6, r4, image or "image missing"),
        result("05-5", "부하·latency·throughput·GPU·queue 기준선", 6, r5, "vllm-evidence ConfigMap"),
    ]


def registry_resources(oc: Oc, ns: str) -> dict[str, Any]:
    inputs = cm_data(oc, "exam-provided-registry-inputs", ns)
    registry_namespace = inputs.get("registry_namespace", "")
    service = inputs.get("registry_service", "")
    port = inputs.get("registry_service_port", "http-api")
    api_path = inputs.get("registry_rest_api", "")
    if not all(non_todo(value) for value in (registry_namespace, service, port, api_path)):
        return {}

    proxy = (
        f"/api/v1/namespaces/{registry_namespace}/services/"
        f"{service}:{port}/proxy{api_path}"
    )
    model_list = oc.raw_json(f"{proxy}/registered_models") or {}
    model = next(
        (item for item in model_list.get("items", []) if item.get("name") == "fraud-risk"),
        None,
    )
    if not model or not non_todo(model.get("id")):
        return {"inputs": inputs, "api_path": api_path, "proxy": proxy}

    versions_list = oc.raw_json(
        f"{proxy}/registered_models/{model['id']}/versions"
    ) or {}
    versions = {
        item.get("name"): item
        for item in versions_list.get("items", [])
        if item.get("name") in {"1.0.0", "1.1.0"}
    }
    artifacts: dict[str, list[dict[str, Any]]] = {}
    for version_name, version in versions.items():
        version_id = version.get("id")
        response = oc.raw_json(f"{proxy}/model_versions/{version_id}/artifacts") or {}
        artifacts[version_name] = response.get("items", []) or []
    return {
        "inputs": inputs,
        "api_path": api_path,
        "proxy": proxy,
        "model": model,
        "versions": versions,
        "artifacts": artifacts,
    }


def registry_metadata_matches(
    evidence: dict[str, str],
    model: dict[str, Any],
    version: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> bool:
    combined = json.dumps([model, version, *artifacts], ensure_ascii=False, sort_keys=True)
    for key in (
        "git_revision", "data_reference", "pipeline_run", "metrics",
        "intended_use", "limitations", "owner", "approval",
    ):
        value = evidence.get(key)
        if not non_todo(value) or key not in combined or str(value) not in combined:
            return False
    expected_format = str(evidence.get("format", "")).lower()
    return non_todo(expected_format) and any(
        str(item.get("modelFormatName", "")).lower() == expected_format
        for item in artifacts
    )


def artifact_has_digest(
    artifacts: list[dict[str, Any]],
    digest: str,
    repository: str,
) -> bool:
    normalized = str(digest or "").removeprefix("sha256:")
    return non_todo(repository) and is_sha(digest) and any(
        normalized in str(item.get("uri", "")).lower()
        and repository in str(item.get("uri", ""))
        for item in artifacts
    )


def grade_06(oc: Oc, ns: str) -> list[Result]:
    evidence = cm_data(oc, "registry-evidence", ns)
    live = registry_resources(oc, ns)
    model = live.get("model") or {}
    versions = live.get("versions") or {}
    version_1_0 = versions.get("1.0.0") or {}
    version_1_1 = versions.get("1.1.0") or {}
    artifacts = live.get("artifacts") or {}
    r1 = has_values(evidence, ["model_id", "version_1_0_id", "version_1_1_id"]) \
        and str(evidence.get("model_id")) == str(model.get("id")) \
        and str(evidence.get("version_1_0_id")) == str(version_1_0.get("id")) \
        and str(evidence.get("version_1_1_id")) == str(version_1_1.get("id")) \
        and str(version_1_0.get("id")) != str(version_1_1.get("id"))

    inputs = live.get("inputs") or {}
    repository = "/".join(filter(None, [
        str(inputs.get("oci_registry", "")).rstrip("/"),
        str(inputs.get("oci_repository", "")).lstrip("/"),
    ]))
    r2 = artifact_has_digest(
        artifacts.get("1.0.0", []), evidence.get("oci_digest_1_0", ""), repository
    ) and artifact_has_digest(
        artifacts.get("1.1.0", []), evidence.get("oci_digest_1_1", ""), repository
    ) \
        and evidence.get("oci_digest_1_0") != evidence.get("oci_digest_1_1") \
        and is_sha(evidence.get("pulled_artifact_sha256"))
    r3 = registry_metadata_matches(
        evidence, model, version_1_1, artifacts.get("1.1.0", [])
    )
    r4 = evidence.get("registry_api_path") == "/api/model_registry/v1alpha3" \
        and live.get("api_path") == evidence.get("registry_api_path") \
        and is_sha(evidence.get("registry_api_response_sha256")) \
        and bool(model)

    deployments = oc.list("inferenceservice", ns)
    approved_digest = str(evidence.get("oci_digest_1_1", "")).removeprefix("sha256:")
    matching_deployments = [
        item for item in deployments
        if condition_true(item)
        and approved_digest
        and approved_digest in json.dumps(item, sort_keys=True).lower()
        and str(dig(item, "metadata", "labels", "modelregistry.opendatahub.io/registered-model-id", default="")) == str(model.get("id", ""))
        and str(dig(item, "metadata", "labels", "modelregistry.opendatahub.io/model-version-id", default="")) == str(version_1_1.get("id", ""))
        and str(dig(item, "metadata", "labels", "modelregistry.opendatahub.io/name", default="")) == str(inputs.get("registry_name", ""))
    ]
    r5 = evidence.get("deployed_version") == "1.1.0" \
        and is_sha(evidence.get("deployment_artifact_digest")) \
        and str(evidence.get("deployment_artifact_digest", "")).removeprefix("sha256:") == approved_digest \
        and bool(matching_deployments)

    return [
        result("06-1", "fraud-risk identity·두 version", 6, r1, "model_id + 서로 다른 version ID"),
        result("06-2", "서로 다른 OCI digest·pull checksum", 6, r2, "digest 값은 유효성만 검사"),
        result("06-3", "계보 metadata 완성", 6, r3, "source/data/run/metrics/use/approval"),
        result("06-4", "REST v1alpha3 API 응답 증적", 6, r4, "registry_api_response_sha256"),
        result("06-5", "1.1.0 exact artifact Ready 배포 연결", 6, r5, f"matching Ready deployments={len(matching_deployments)}"),
    ]


def grade_07(oc: Oc, ns: str) -> list[Result]:
    service = oc.get("trustyaiservice", "trustyai-service", ns)
    r1 = service is not None and (condition_true(service) or non_todo(dig(service, "status", "phase")))
    capture = cm_data(oc, "monitoring-evidence", ns)
    r1 = r1 and has_values(capture, ["model_identifier", "capture_test_sha256"])
    r2 = has_values(capture, ["protected_attribute", "favorable_outcome", "comparison_groups", "fairness_threshold", "window", "minimum_samples"])
    r3 = has_values(capture, ["reference_dataset_digest", "current_window", "drift_metric", "drift_result"]) and is_sha(capture.get("reference_dataset_digest"))
    r4 = has_values(capture, ["request_latency_panel", "request_error_panel", "cpu_memory_panel", "accelerator_panel", "correlation_window"])
    r5 = has_values(capture, ["signal_owner", "rollback_condition", "redaction_policy", "retention_policy", "access_policy"])

    return [
        result("07-1", "TrustyAIService·capture path", 6, r1, "trustyai-service + monitoring-evidence"),
        result("07-2", "공정성 population·threshold·window", 6, r2, "monitoring-evidence ConfigMap"),
        result("07-3", "고정 reference drift 비교", 6, r3, "reference_dataset_digest"),
        result("07-4", "서비스·자원 동일 시간축 상관", 6, r4, "dashboard references"),
        result("07-5", "owner·rollback·데이터 보호", 6, r5, "redaction/retention/access"),
    ]


def grade_08(oc: Oc, ns: str) -> list[Result]:
    evidence = cm_data(oc, "optimization-evidence", ns)
    r1 = has_values(evidence, ["baseline_model_revision", "runtime_digest", "hardware", "precision", "context_length", "dataset_revision", "seed"]) \
        and is_sha(evidence.get("runtime_digest"))

    job = oc.get("job", "quantize-support-llm", ns)
    r2 = completed_job(job) and is_sha(evidence.get("optimized_artifact_digest")) \
        and evidence.get("llm_compressor_support_status") == "Developer Preview"

    jobs = oc.list("lmevaljob", ns)
    succeeded_jobs = [
        item for item in jobs
        if dig(item, "status", "state") == "Complete"
        and dig(item, "status", "reason") == "Succeeded"
        and non_todo(dig(item, "status", "results"))
    ]
    named_jobs = {
        dig(item, "metadata", "name") for item in succeeded_jobs
    }
    r3 = len(succeeded_jobs) >= 2 \
        and evidence.get("baseline_lmeval_job") in named_jobs \
        and evidence.get("optimized_lmeval_job") in named_jobs \
        and evidence.get("baseline_lmeval_job") != evidence.get("optimized_lmeval_job") \
        and has_values(evidence, ["standard_task", "korean_benchmark", "safety_benchmark", "sample_count", "failed_samples"])
    r4 = has_values(evidence, ["quality_delta", "safety_delta", "p95_latency_delta", "throughput_delta", "memory_delta", "decision", "rollback_uri"]) \
        and non_todo(evidence.get("rollback_uri"))

    return [
        result("08-1", "고정 baseline 계약", 6, r1, "optimization-evidence ConfigMap"),
        result("08-2", "한 가지 최적화·digest·지원 상태", 6, r2, "job/quantize-support-llm"),
        result("08-3", "동일 조건 LMEval 두 실행 성공", 6, r3, f"succeeded={len(succeeded_jobs)}/{len(jobs)}"),
        result("08-4", "품질·성능 비교와 rollback", 6, r4, "comparison + rollback_uri"),
    ]


def deployment_ready(deployment: dict[str, Any] | None) -> bool:
    desired = int(dig(deployment, "spec", "replicas", default=1) or 1)
    available = int(dig(deployment, "status", "availableReplicas", default=0) or 0)
    return available >= desired


def grade_09(oc: Oc, ns: str) -> list[Result]:
    evidence = cm_data(oc, "rag-evidence", ns)
    r2 = has_values(evidence, ["source_id", "source_revision", "document_acl", "embedding_model_revision", "index_digest"]) and is_sha(evidence.get("index_digest"))

    role = oc.get("role", "rag-reader", ns)
    role_rules = (role or {}).get("rules", []) or []
    role_ok = len(role_rules) == 1 and all(
        set(rule.get("apiGroups", []) or []) == {""}
        and set(rule.get("resources", []) or []) == {"configmaps"}
        and set(rule.get("resourceNames", []) or []) == {"rag-documents"}
        and set(rule.get("verbs", []) or []) == {"get"}
        for rule in role_rules
    )
    network_policies = oc.list("networkpolicy", ns)
    rolebindings = oc.list("rolebinding", ns)
    def exact_rag_binding(binding: dict[str, Any]) -> bool:
        subjects = binding.get("subjects", []) or []
        return dig(binding, "roleRef", "kind") == "Role" \
            and dig(binding, "roleRef", "name") == "rag-reader" \
            and len(subjects) == 1 \
            and subjects[0].get("kind") == "ServiceAccount" \
            and subjects[0].get("name") == "rag-app" \
            and subjects[0].get("namespace", ns) == ns \
            and subjects[0].get("apiGroup", "") == ""

    binding_ok = any(exact_rag_binding(binding) for binding in rolebindings)

    def restricted_egress(policy: dict[str, Any]) -> bool:
        spec = policy.get("spec", {}) or {}
        if dig(spec, "podSelector", "matchLabels", "app") != "genai-app":
            return False
        if "Egress" not in (spec.get("policyTypes", []) or []):
            return False
        egress = spec.get("egress", []) or []
        if not egress:
            return False
        destinations: set[str] = set()
        dns_ok = False
        for rule in egress:
            peers = rule.get("to", []) or []
            ports = rule.get("ports", []) or []
            if not peers or not ports:
                return False
            for peer in peers:
                if not peer or dig(peer, "ipBlock", "cidr") in {"0.0.0.0/0", "::/0"}:
                    return False
                app = dig(peer, "podSelector", "matchLabels", "app")
                if app:
                    if app not in {"mock-llm", "todo-tool"} \
                            or any(str(port.get("port")) != "8080" or port.get("protocol", "TCP") != "TCP" for port in ports):
                        return False
                    destinations.add(app)
                    continue
                namespace_name = dig(
                    peer, "namespaceSelector", "matchLabels", "kubernetes.io/metadata.name"
                )
                dns_ports = {
                    (str(port.get("port")), port.get("protocol", "TCP"))
                    for port in ports
                }
                if namespace_name != "openshift-dns" or dns_ports != {
                    ("53", "UDP"), ("53", "TCP"),
                    ("5353", "UDP"), ("5353", "TCP"),
                }:
                    return False
                dns_ok = True
        return destinations == {"mock-llm", "todo-tool"} and dns_ok

    network_ok = any(restricted_egress(policy) for policy in network_policies)
    r3 = role_ok and binding_ok and network_ok

    verifier_cm = oc.get("configmap", "exam-provided-rag-verifier", ns)
    verifier_source = dig(verifier_cm, "data", "verify_rag.py", default="")
    verifier_hash_ok = hashlib.sha256(verifier_source.encode()).hexdigest() == RAG_VERIFIER_SHA256
    verifier_job = oc.get("job", "rag-contract-verification", ns)
    job_container = dig(verifier_job, "spec", "template", "spec", "containers", 0, default={}) or {}
    job_volumes = dig(verifier_job, "spec", "template", "spec", "volumes", default=[]) or []
    verifier_job_ok = completed_job(verifier_job) \
        and verifier_hash_ok \
        and job_container.get("image") == RAG_VERIFIER_IMAGE \
        and job_container.get("command") == ["python", "/verify/verify_rag.py"] \
        and any(
            volume.get("configMap", {}).get("name") == "exam-provided-rag-verifier"
            for volume in job_volumes
        ) \
        and any(
            mount.get("mountPath") == "/verify" and mount.get("readOnly") is True
            for mount in (job_container.get("volumeMounts", []) or [])
        )
    r4 = evidence.get("unauthorized_retrieval_count") == "0" \
        and evidence.get("stream_http", "").startswith("2") \
        and has_values(evidence, ["citation_response_sha256"]) \
        and verifier_job_ok
    r5 = has_values(evidence, ["tool_schema_sha256", "tool_timeout_seconds", "tool_step_limit", "tool_audit_sha256"]) \
        and evidence.get("tool_read_only", "").lower() == "true" \
        and verifier_job_ok
    r6 = has_values(evidence, ["direct_injection", "indirect_injection", "unauthorized_document", "malformed_tool_argument", "dependency_outage", "false_positive_test"]) \
        and all(evidence.get(key, "").lower() == "pass" for key in ["direct_injection", "indirect_injection", "unauthorized_document", "malformed_tool_argument", "dependency_outage", "false_positive_test"]) \
        and verifier_job_ok

    return [
        result("09-1", "버전된 ingestion·ACL·index digest", 6, r2, "rag-evidence ConfigMap"),
        result("09-2", "retrieval 전 권한 경계·최소 권한", 6, r3, f"Role={role_ok}, RoleBinding={binding_ok}, NetworkPolicy={network_ok}"),
        result("09-3", "unauthorized=0·streaming·citation", 6, r4, f"fixed verifier Job={verifier_job_ok}"),
        result("09-4", "read-only typed tool·timeout·audit", 6, r5, f"fixed verifier Job={verifier_job_ok}"),
        result("09-5", "주입·권한·오류·장애 시험", 6, r6, f"6-case fixed verifier Job={verifier_job_ok}"),
    ]


def grade_10(oc: Oc, ns: str) -> list[Result]:
    evidence = cm_data(oc, "evidence-manifest", ns)
    r1 = has_values(evidence, ["git_sha", "environment_lock_sha256", "pipeline_definition_sha256", "secret_scan_result"]) \
        and evidence.get("secret_scan_result", "").lower() == "pass"
    r2 = has_values(evidence, ["export_format", "model_sha256", "clean_load_test", "sample_inference_sha256"]) \
        and evidence.get("clean_load_test", "").lower() == "pass" \
        and is_sha(evidence.get("model_sha256")) and is_sha(evidence.get("sample_inference_sha256"))
    lineage_keys = ["image_digest", "data_digest", "pipeline_run_id", "model_digest", "index_digest", "metric", "approval", "deployment_digest", "monitoring_link"]
    r3 = has_values(evidence, lineage_keys) \
        and all(is_sha(evidence.get(key)) for key in ["image_digest", "data_digest", "model_digest", "index_digest", "deployment_digest"])

    replay = oc.get("job", "clean-replay", ns)
    rollback = cm_data(oc, "rollback-evidence", ns)
    r4 = completed_job(replay) and has_values(rollback, ["previous_model_digest", "previous_runtime_digest", "endpoint_http", "protocol_test_sha256", "verified_at"]) \
        and rollback.get("endpoint_http", "").startswith("2") \
        and is_sha(rollback.get("previous_model_digest")) and is_sha(rollback.get("previous_runtime_digest"))

    return [
        result("10-1", "clean Git·lock·secret scan", 6, r1, "evidence-manifest ConfigMap"),
        result("10-2", "model export·clean load/inference", 6, r2, "model/sample digest"),
        result("10-3", "source→data→run→model→배포 계보", 6, r3, "evidence-manifest ConfigMap"),
        result("10-4", "clean replay Job·rollback 재검증", 6, r4, "job/clean-replay + rollback-evidence"),
    ]


GRADERS: dict[str, Callable[[Oc, str], list[Result]]] = {
    "01": grade_01,
    "02": grade_02,
    "03": grade_03,
    "04": grade_04,
    "05": grade_05,
    "06": grade_06,
    "07": grade_07,
    "08": grade_08,
    "09": grade_09,
    "10": grade_10,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=sorted(TASKS))
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    namespace, maximum, title = TASKS[args.task]
    oc = Oc()
    if oc.run("whoami").returncode != 0:
        print("OpenShift에 먼저 로그인하세요: oc login ...", file=sys.stderr)
        return 2

    results = GRADERS[args.task](oc, namespace)
    earned = sum(item.points for item in results if item.passed)

    if args.as_json:
        print(json.dumps({
            "task": args.task,
            "title": title,
            "namespace": namespace,
            "earned": earned,
            "maximum": maximum,
            "passed": earned == maximum,
            "checks": [asdict(item) for item in results],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"Task {args.task} · {title} · namespace {namespace}")
        print("=" * 72)
        for item in results:
            mark = "PASS" if item.passed else "FAIL"
            score = item.points if item.passed else 0
            print(f"[{mark}] {item.check_id}  {score:>2}/{item.points}  {item.description}")
            print(f"       {item.detail}")
        print("-" * 72)
        print(f"SCORE: {earned}/{maximum}")

    return 0 if earned == maximum else 1


if __name__ == "__main__":
    raise SystemExit(main())

