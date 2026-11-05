#!/usr/bin/env python3
"""EX267 v3.3 practice-lab resource grader.

The grader reads Kubernetes/OpenShift resources only. It never prints Secret data.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
import json
import re
import subprocess
import sys
from typing import Any, Callable


TASKS = {
    "01": ("ex267-fraud", 24, "프로젝트·RBAC·S3 연결"),
    "02": ("ex267-t02-workbench", 30, "Workbench·PVC·실험 증적"),
    "03": ("ex267-t03-pipeline", 36, "KFP v2 Pipeline·실험 비교"),
    "04": ("ex267-t04-serving", 36, "OpenVINO KServe 모델 서빙"),
    "05": ("ex267-t05-vllm", 30, "vLLM·GPU 배치 진단"),
    "06": ("ex267-t06-registry", 30, "Model Registry·계보"),
    "07": ("ex267-t07-monitoring", 30, "TrustyAI·플랫폼 모니터링"),
    "08": ("ex267-t08-evaluation", 24, "LLM 최적화·LMEval"),
    "09": ("ex267-t09-rag", 36, "Guardrailed RAG"),
    "10": ("ex267-t10-evidence", 24, "재현·증적·롤백"),
}

SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
PINNED_IMAGE = re.compile(r"@sha256:[0-9a-f]{64}$")
TODO_VALUES = {"", "todo", "replace_me", "replace-me", "pending", "unknown", "n/a"}


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


def result(check_id: str, description: str, points: int, passed: bool, detail: str) -> Result:
    return Result(check_id, description, points, bool(passed), detail)


def grade_01(oc: Oc, ns: str) -> list[Result]:
    namespace = oc.get("namespace", ns)
    labels = dig(namespace, "metadata", "labels", default={}) or {}
    r1 = labels.get("team") == "northstar-risk" and labels.get("environment") == "exam"

    rolebindings = oc.list("rolebinding", ns)
    roles_for_user: list[str] = []
    for binding in rolebindings:
        subjects = binding.get("subjects", []) or []
        if any(subject.get("kind") == "User" and subject.get("name") == "developer1" for subject in subjects):
            roles_for_user.append(dig(binding, "roleRef", "name", default=""))
    r2 = "edit" in roles_for_user and not ({"admin", "cluster-admin"} & set(roles_for_user))

    connection = oc.get("secret", "fraud-s3", ns)
    annotation = dig(connection, "metadata", "annotations", "opendatahub.io/connection-type-protocol")
    r3 = annotation == "s3" and secret_values_are_real(
        connection,
        ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT", "AWS_S3_BUCKET"],
    )

    evidence = cm_data(oc, "fraud-s3-evidence", ns)
    r4 = has_values(evidence, ["input_key", "output_key", "input_sha256", "output_sha256", "verified_from_new_process"]) \
        and is_sha(evidence.get("input_sha256")) and is_sha(evidence.get("output_sha256")) \
        and evidence.get("verified_from_new_process", "").lower() == "true"

    return [
        result("01-1", "프로젝트 팀·환경 라벨", 6, r1, "team=northstar-risk, environment=exam"),
        result("01-2", "developer1 최소 권한 edit RoleBinding", 6, r2, f"roles={roles_for_user or ['none']}"),
        result("01-3", "fraud-s3 protocol·endpoint·bucket·Secret", 6, r3, "Secret 값은 출력하지 않음"),
        result("01-4", "새 프로세스 read/write SHA-256 증적", 6, r4, "fraud-s3-evidence ConfigMap"),
    ]


def grade_02(oc: Oc, ns: str) -> list[Result]:
    notebook = oc.get("notebook", "risk-lab", ns)
    container = dig(notebook, "spec", "template", "spec", "containers", 0, default={}) or {}
    image = container.get("image", "")
    r1 = bool(PINNED_IMAGE.search(image))

    volumes = dig(notebook, "spec", "template", "spec", "volumes", default=[]) or []
    mounts = container.get("volumeMounts", []) or []
    claim_names = [dig(volume, "persistentVolumeClaim", "claimName") for volume in volumes]
    storage_claim = next((name for name in claim_names if name), None)
    pvc = oc.get("pvc", storage_claim, ns) if storage_claim else None
    storage = dig(pvc, "spec", "resources", "requests", "storage", default="")
    mounted = any(mount.get("mountPath") == "/opt/app-root/src" for mount in mounts)
    r2 = storage in {"10Gi", "10240Mi"} and mounted

    resources = container.get("resources", {}) or {}
    requests = resources.get("requests", {}) or {}
    limits = resources.get("limits", {}) or {}
    r3 = all(non_todo(values.get(key)) for values in (requests, limits) for key in ("cpu", "memory"))

    evidence = cm_data(oc, "workbench-evidence", ns)
    r4 = has_values(evidence, ["git_revision", "data_version", "seed", "image_digest", "artifact_uri"]) \
        and is_sha(evidence.get("image_digest"))
    try:
        runs = int(evidence.get("tensorboard_runs", "0"))
    except ValueError:
        runs = 0
    r5 = runs >= 2 and evidence.get("restart_proof", "").lower() == "true"

    return [
        result("02-1", "risk-lab 승인 image digest", 6, r1, image or "Notebook 없음"),
        result("02-2", "10Gi PVC와 /opt/app-root/src mount", 6, r2, f"claim={storage_claim}, size={storage or 'none'}"),
        result("02-3", "CPU·memory request/limit", 6, r3, json.dumps(resources, ensure_ascii=False)),
        result("02-4", "실험 재현 metadata", 6, r4, "workbench-evidence ConfigMap"),
        result("02-5", "재시작 영속성과 TensorBoard 2개 run", 6, r5, f"runs={runs}"),
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

    return [
        result("03-1", "DSPA Ready", 6, r1, "dspa/dspa"),
        result("03-2", "validate·train·evaluate 독립 컴포넌트", 6, r2, "fraud-training-pipeline ConfigMap"),
        result("03-3", "KFP SDK 2.14.3+ compiled definition", 6, r3, f"kfp={sdk_version or 'missing'}"),
        result("03-4", "ServiceAccount·Secret·resources", 6, r4, "pipeline-evidence ConfigMap"),
        result("03-5", "cache·retry·run prefix 안전성", 6, r5, "pipeline-evidence ConfigMap"),
        result("03-6", "서로 다른 max_depth 두 run과 승인 모델", 6, r6, f"succeeded={len(workflows)}, depths={sorted(depths)}"),
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
    r2 = "openvino" in runtime and model_format in {"onnx", "openvino_ir", "openvino"}

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

    return [
        result("04-1", "models/fraud/2 immutable artifact", 6, r1, f"storage={uri or connection_path or 'missing'}"),
        result("04-2", "OpenVINO runtime·model format", 6, r2, f"runtime={runtime}, format={model_format}"),
        result("04-3", "1 CPU·2Gi request/limit", 6, r3, json.dumps(resources, ensure_ascii=False)),
        result("04-4", "InferenceService Ready·URL", 6, r4, "fraud-v2"),
        result("04-5", "V2 정상·invalid shape 응답", 6, r5, f"normal={normal_http or 'none'}, invalid={invalid_http or 'none'}"),
        result("04-6", "재생성·rollback 재검증", 6, r6, "serving-evidence ConfigMap"),
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


def grade_06(oc: Oc, ns: str) -> list[Result]:
    evidence = cm_data(oc, "registry-evidence", ns)
    registries = oc.list_all("modelregistries.modelregistry.opendatahub.io")
    available_registries = [
        registry for registry in registries
        if condition_true(registry, "Available") or condition_true(registry)
    ]
    r1 = bool(available_registries) \
        and has_values(evidence, ["model_id", "version_1_0_id", "version_1_1_id"]) \
        and evidence.get("version_1_0_id") != evidence.get("version_1_1_id")
    r2 = is_sha(evidence.get("oci_digest_1_0")) and is_sha(evidence.get("oci_digest_1_1")) \
        and evidence.get("oci_digest_1_0") != evidence.get("oci_digest_1_1") \
        and is_sha(evidence.get("pulled_artifact_sha256"))
    r3 = has_values(evidence, ["git_revision", "data_reference", "pipeline_run", "format", "metrics", "intended_use", "limitations", "owner", "approval"])
    r4 = has_values(evidence, ["v1beta1_response_sha256", "registry_endpoint"]) and is_sha(evidence.get("v1beta1_response_sha256"))
    r5 = evidence.get("deployed_version") == "1.1.0" \
        and is_sha(evidence.get("deployment_artifact_digest")) \
        and str(evidence.get("deployment_artifact_digest", "")).removeprefix("sha256:") == str(evidence.get("oci_digest_1_1", "")).removeprefix("sha256:")

    return [
        result("06-1", "Available Registry·fraud-risk identity·두 version", 6, r1, f"registries={len(available_registries)}"),
        result("06-2", "서로 다른 OCI digest·pull checksum", 6, r2, "digest 값은 유효성만 검사"),
        result("06-3", "계보 metadata 완성", 6, r3, "source/data/run/metrics/use/approval"),
        result("06-4", "v1beta1 API 응답 증적", 6, r4, "v1beta1_response_sha256"),
        result("06-5", "1.1.0 exact artifact 배포 연결", 6, r5, "deployed_version=1.1.0"),
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
    app = oc.get("deployment", "genai-app", ns)
    route = oc.get("route", "genai-app", ns)
    r1 = deployment_ready(app) and route is not None

    evidence = cm_data(oc, "rag-evidence", ns)
    r2 = has_values(evidence, ["source_id", "source_revision", "document_acl", "embedding_model_revision", "index_digest"]) and is_sha(evidence.get("index_digest"))
    network_policies = oc.list("networkpolicy", ns)
    rolebindings = oc.list("rolebinding", ns)
    r3 = bool(network_policies) and any(
        dig(binding, "roleRef", "name") not in {"admin", "cluster-admin"}
        and any(
            subject.get("kind") == "ServiceAccount"
            and subject.get("name") == "rag-app"
            and subject.get("namespace", ns) == ns
            for subject in (binding.get("subjects", []) or [])
        )
        for binding in rolebindings
    )
    r4 = evidence.get("unauthorized_retrieval_count") == "0" \
        and evidence.get("stream_http", "").startswith("2") \
        and has_values(evidence, ["citation_response_sha256"])
    r5 = has_values(evidence, ["tool_schema_sha256", "tool_timeout_seconds", "tool_step_limit", "tool_audit_sha256"]) \
        and evidence.get("tool_read_only", "").lower() == "true"
    r6 = has_values(evidence, ["direct_injection", "indirect_injection", "unauthorized_document", "malformed_tool_argument", "dependency_outage", "false_positive_test"]) \
        and all(evidence.get(key, "").lower() == "pass" for key in ["direct_injection", "indirect_injection", "unauthorized_document", "malformed_tool_argument", "dependency_outage", "false_positive_test"])

    return [
        result("09-1", "RAG 애플리케이션 Ready·Route", 6, r1, "deployment/route genai-app"),
        result("09-2", "버전된 ingestion·ACL·index digest", 6, r2, "rag-evidence ConfigMap"),
        result("09-3", "retrieval 전 권한 경계·최소 권한", 6, r3, f"NetworkPolicies={len(network_policies)}"),
        result("09-4", "unauthorized=0·streaming·citation", 6, r4, "rag-evidence ConfigMap"),
        result("09-5", "read-only typed tool·timeout·audit", 6, r5, "rag-evidence ConfigMap"),
        result("09-6", "주입·권한·오류·장애 시험", 6, r6, "6-case matrix"),
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

