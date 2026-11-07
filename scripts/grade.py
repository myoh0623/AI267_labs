#!/usr/bin/env python3
"""Graders for the AI267 3.3 practice tasks.

Checks are read-only except Task 05's short-lived verification Job. That Job mounts
the stopped Workbench PVC read-only, emits booleans only, and is deleted in finally.
"""

from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import re
import runpy
import secrets
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "tasks" / "catalog.tsv"
ELYRA_RUNTIME_DISPLAY_NAME = "forecast-pipeline-runtime"
ELYRA_RUNTIME_IMAGE = "registry.lab.example.com:8443/redhattraining/dspa-elyra-runtime:v2.0"


@dataclass(frozen=True)
class Task:
    task_id: str
    slug: str
    lab: str
    namespace: str
    title: str
    points: int


@dataclass(frozen=True)
class Check:
    check_id: str
    title: str
    passed: bool
    detail: str
    points: int = 20


def load_tasks() -> dict[str, Task]:
    tasks: dict[str, Task] = {}
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        task_id, slug, lab, namespace, title, points = line.split("\t")
        tasks[task_id] = Task(task_id, slug, lab, namespace, title, int(points))
    return tasks


TASKS = load_tasks()


class Oc:
    def run(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["oc", *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                ["oc", *args],
                124,
                stdout=str(exc.stdout or ""),
                stderr=f"oc command timed out after {timeout}s",
            )

    def run_input(
        self,
        input_text: str,
        *args: str,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["oc", *args],
                input=input_text,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                ["oc", *args],
                124,
                stdout=str(exc.stdout or ""),
                stderr=f"oc command timed out after {timeout}s",
            )

    def get(self, kind: str, name: str, namespace: str | None = None) -> dict[str, Any] | None:
        args = ["get", kind, name]
        if namespace:
            args += ["-n", namespace]
        args += ["-o", "json"]
        result = self.run(*args)
        if result.returncode:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    def list(self, kind: str, namespace: str | None = None) -> list[dict[str, Any]]:
        args = ["get", kind]
        if namespace:
            args += ["-n", namespace]
        else:
            args.append("-A")
        args += ["-o", "json"]
        result = self.run(*args)
        if result.returncode:
            return []
        try:
            return json.loads(result.stdout).get("items", [])
        except json.JSONDecodeError:
            return []

    def exec(
        self,
        namespace: str,
        pod: str,
        container: str,
        command: list[str],
        timeout: int = 45,
    ) -> subprocess.CompletedProcess[str]:
        return self.run(
            "exec",
            "-n",
            namespace,
            pod,
            "-c",
            container,
            "--",
            *command,
            timeout=timeout,
        )


def dig(value: Any, *path: Any, default: Any = None) -> Any:
    current = value
    for key in path:
        try:
            if isinstance(key, int):
                current = current[key]
            else:
                current = current.get(key)
        except (AttributeError, IndexError, KeyError, TypeError):
            return default
        if current is None:
            return default
    return current


def check(check_id: str, title: str, passed: bool, detail: str) -> Check:
    return Check(check_id, title, bool(passed), detail)


def ready(resource: dict[str, Any] | None, condition: str = "Ready") -> bool:
    conditions = dig(resource, "status", "conditions", default=[]) or []
    return any(
        item.get("type") == condition and str(item.get("status")).lower() == "true"
        for item in conditions
    )


def phase(resource: dict[str, Any] | None) -> str:
    return str(dig(resource, "status", "phase", default=""))


def annotations(resource: dict[str, Any] | None) -> dict[str, str]:
    return dig(resource, "metadata", "annotations", default={}) or {}


def labels(resource: dict[str, Any] | None) -> dict[str, str]:
    return dig(resource, "metadata", "labels", default={}) or {}


def resource_name(resource: dict[str, Any] | None) -> str:
    return str(dig(resource, "metadata", "name", default=""))


def first_container(resource: dict[str, Any] | None) -> dict[str, Any]:
    containers = dig(resource, "spec", "template", "spec", "containers", default=[]) or []
    return containers[0] if containers else {}


def secret_data(secret: dict[str, Any] | None) -> dict[str, str]:
    decoded: dict[str, str] = {}
    for key, value in (dig(secret, "data", default={}) or {}).items():
        try:
            decoded[key] = base64.b64decode(value).decode("utf-8")
        except Exception:
            decoded[key] = ""
    decoded.update(dig(secret, "stringData", default={}) or {})
    return decoded


def group_users(group: dict[str, Any] | None) -> set[str]:
    return set(dig(group, "users", default=[]) or [])


def role_for_user(oc: Any, namespace: str, user: str, accepted_roles: set[str]) -> bool:
    for binding in oc.list("rolebinding.rbac.authorization.k8s.io", namespace):
        role = str(dig(binding, "roleRef", "name", default=""))
        if role not in accepted_roles:
            continue
        for subject in dig(binding, "subjects", default=[]) or []:
            if subject.get("kind") == "User" and subject.get("name") == user:
                return True
    return False


def roles_for_user(oc: Any, namespace: str, user: str) -> set[str]:
    roles: set[str] = set()
    for binding in oc.list("rolebinding.rbac.authorization.k8s.io", namespace):
        if any(
            subject.get("kind") == "User" and subject.get("name") == user
            for subject in (dig(binding, "subjects", default=[]) or [])
        ):
            roles.add(str(dig(binding, "roleRef", "name", default="")))
    return roles


def dangerous_cluster_binding(
    oc: Any,
    *,
    users: set[str] | None = None,
    groups: set[str] | None = None,
) -> bool:
    users = users or set()
    groups = groups or set()
    dangerous_roles = {"cluster-admin", "admin", "rhods-admin", "ods-admin"}
    for binding in oc.list("clusterrolebinding.rbac.authorization.k8s.io"):
        if str(dig(binding, "roleRef", "name", default="")).lower() not in dangerous_roles:
            continue
        for subject in dig(binding, "subjects", default=[]) or []:
            if subject.get("kind") == "User" and subject.get("name") in users:
                return True
            if subject.get("kind") == "Group" and subject.get("name") in groups:
                return True
    return False


def notebook_pod(oc: Any, namespace: str, notebook_name: str) -> tuple[str, str] | None:
    try:
        pods = oc.list("pod", namespace)
    except Exception:
        return None
    candidates: list[dict[str, Any]] = []
    for pod in pods:
        pod_labels = labels(pod)
        name = resource_name(pod)
        if (
            pod_labels.get("notebook-name") == notebook_name
            or pod_labels.get("app") == notebook_name
            or name == f"{notebook_name}-0"
            or name.startswith(f"{notebook_name}-")
        ):
            candidates.append(pod)
    if not candidates:
        return None
    candidates.sort(key=lambda item: resource_name(item))
    pod = candidates[0]
    containers = dig(pod, "spec", "containers", default=[]) or []
    names = [item.get("name", "") for item in containers]
    container = next(
        (name for name in names if name and name not in {"oauth-proxy", "kube-rbac-proxy"}),
        names[0] if names else "",
    )
    return resource_name(pod), container


def pod_is_ready(oc: Any, namespace: str, notebook_name: str) -> bool:
    location = notebook_pod(oc, namespace, notebook_name)
    if not location:
        return False
    pod = oc.get("pod", location[0], namespace)
    statuses = dig(pod, "status", "containerStatuses", default=[]) or []
    return phase(pod) == "Running" and bool(statuses) and all(
        bool(item.get("ready")) for item in statuses
    )


def exec_notebook(
    oc: Any,
    namespace: str,
    notebook_name: str,
    command: list[str],
    timeout: int = 45,
) -> subprocess.CompletedProcess[str] | None:
    location = notebook_pod(oc, namespace, notebook_name)
    if not location or not hasattr(oc, "exec"):
        return None
    try:
        return oc.exec(namespace, location[0], location[1], command, timeout=timeout)
    except Exception:
        return None


def exec_ok(
    oc: Any,
    namespace: str,
    notebook_name: str,
    command: list[str],
    timeout: int = 45,
) -> bool:
    result = exec_notebook(oc, namespace, notebook_name, command, timeout)
    return bool(result and result.returncode == 0)


def exec_stdout(
    oc: Any,
    namespace: str,
    notebook_name: str,
    command: list[str],
    timeout: int = 45,
) -> str:
    result = exec_notebook(oc, namespace, notebook_name, command, timeout)
    return result.stdout if result and result.returncode == 0 else ""


def notebook_references(resource: dict[str, Any] | None, name: str) -> bool:
    if not resource:
        return False
    return name in json.dumps(resource, ensure_ascii=False)


def notebook_uses_hardware_profile(
    notebook: dict[str, Any] | None,
    name: str,
    namespace: str,
) -> bool:
    note = annotations(notebook)
    return (
        note.get("opendatahub.io/hardware-profile-name") == name
        and note.get("opendatahub.io/hardware-profile-namespace") == namespace
    )


def notebook_image_is(
    notebook: dict[str, Any] | None,
    *,
    display_name: str,
    image_tokens: tuple[str, ...],
) -> bool:
    note = annotations(notebook)
    if note.get("opendatahub.io/image-display-name") == display_name:
        return True
    selected = str(note.get("notebooks.opendatahub.io/last-image-selection", "")).lower()
    image = str(first_container(notebook).get("image", "")).lower()
    return all(token.lower() in f"{selected} {image}" for token in image_tokens)


def notebook_image_version_is(
    notebook: dict[str, Any] | None,
    version: str,
) -> bool:
    """Match an exact workbench image tag, never a version substring.

    The Dashboard records the selected ImageStreamTag in
    ``notebooks.opendatahub.io/last-image-selection``. Some manifests retain a
    tagged container reference instead, so both documented representations are
    accepted.
    """

    candidates = (
        annotations(notebook).get("notebooks.opendatahub.io/last-image-selection", ""),
        first_container(notebook).get("image", ""),
    )
    for candidate in candidates:
        reference = str(candidate).strip()
        if "@" in reference:
            continue
        final_segment = reference.rsplit("/", 1)[-1]
        _, separator, tag = final_segment.rpartition(":")
        if separator and tag == version:
            return True
    return False


def notebook_has_source(
    notebook: dict[str, Any] | None,
    source_kind: str,
    source_name: str,
) -> bool:
    key = f"{source_kind}Ref"
    return any(
        dig(item, key, "name") == source_name
        for item in (first_container(notebook).get("envFrom", []) or [])
    )


def notebook_has_connection(
    notebook: dict[str, Any] | None,
    namespace: str,
    connection_name: str,
) -> bool:
    raw = str(annotations(notebook).get("opendatahub.io/connections", ""))
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, list):
        references = {str(item).strip() for item in decoded if str(item).strip()}
    else:
        references = {
            item.strip().strip("[]\"'")
            for item in raw.split(",")
            if item.strip().strip("[]\"'")
        }
    prefix = "aws-connection-"
    logical_name = (
        connection_name[len(prefix) :]
        if connection_name.startswith(prefix)
        else connection_name
    )
    secret_name = f"{prefix}{logical_name}"
    names = {logical_name, secret_name}
    accepted = names | {f"{namespace}/{name}" for name in names}
    return bool(references & accepted) or any(
        notebook_has_source(notebook, "secret", name) for name in names
    )


def notebook_has_pvc(notebook: dict[str, Any] | None, claim_name: str) -> bool:
    volumes = dig(notebook, "spec", "template", "spec", "volumes", default=[]) or []
    return any(dig(volume, "persistentVolumeClaim", "claimName") == claim_name for volume in volumes)


def notebook_has_bound_storage(
    oc: Any,
    namespace: str,
    notebook: dict[str, Any] | None,
    accepted_sizes: set[str],
) -> bool:
    volumes = dig(notebook, "spec", "template", "spec", "volumes", default=[]) or []
    claims = {
        str(dig(volume, "persistentVolumeClaim", "claimName", default=""))
        for volume in volumes
    }
    for claim in claims - {""}:
        pvc = oc.get("pvc", claim, namespace)
        size = str(dig(pvc, "spec", "resources", "requests", "storage", default=""))
        if phase(pvc) == "Bound" and size in accepted_sizes:
            return True
    return False


def notebook_code(content: str) -> str:
    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return ""
    sources: list[str] = []
    for cell in document.get("cells", []) or []:
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        sources.append("".join(source) if isinstance(source, list) else str(source))
    return "\n".join(sources)


def notebook_ran_without_errors(content: str) -> bool:
    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False
    code_cells = [cell for cell in (document.get("cells", []) or []) if cell.get("cell_type") == "code"]
    substantive = []
    for cell in code_cells:
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        if text.strip():
            substantive.append(cell)
    return bool(substantive) and all(
        cell.get("execution_count") is not None
        and not any(output.get("output_type") == "error" for output in (cell.get("outputs", []) or []))
        for cell in substantive
    )


def notebook_cell_executed(content: str, marker: str) -> bool:
    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False
    for cell in document.get("cells", []) or []:
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        if marker not in text:
            continue
        return cell.get("execution_count") is not None and not any(
            output.get("output_type") == "error" for output in (cell.get("outputs", []) or [])
        )
    return False


def _python_ast_for_notebook_cell(text: str) -> ast.Module | None:
    """Parse Python from a cell while tolerating IPython line magics/shell lines."""

    python_lines = [
        "pass" if line.lstrip().startswith(("%", "!")) else line
        for line in text.splitlines()
    ]
    try:
        return ast.parse("\n".join(python_lines))
    except SyntaxError:
        return None


def notebook_has_exact_scatter_plot(content: str) -> bool:
    """Check the source-prescribed -50..50 Plotly scatter and fig.show()."""

    code = notebook_code(content)
    tree = _python_ast_for_notebook_cell(code)
    if tree is None:
        return False

    exact_range = False
    scatter_assigned_to_fig = False
    fig_show = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "show"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "fig"
            ):
                fig_show = True
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if (
            isinstance(value, ast.Call)
            and (
                (isinstance(value.func, ast.Attribute) and value.func.attr == "linspace")
                or (isinstance(value.func, ast.Name) and value.func.id == "linspace")
            )
            and any(isinstance(target, ast.Name) and target.id == "x" for target in targets)
        ):
            values: dict[str, ast.AST] = {}
            if value.args:
                values["start"] = value.args[0]
            if len(value.args) > 1:
                values["stop"] = value.args[1]
            values.update(
                {keyword.arg: keyword.value for keyword in value.keywords if keyword.arg}
            )
            try:
                start = ast.literal_eval(values["start"])
                stop = ast.literal_eval(values["stop"])
            except (KeyError, ValueError, TypeError):
                pass
            else:
                exact_range = exact_range or (
                    not isinstance(start, bool)
                    and not isinstance(stop, bool)
                    and start == -50
                    and stop == 50
                )
        if not (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "scatter"
        ):
            continue
        scatter_assigned_to_fig = scatter_assigned_to_fig or any(
            isinstance(target, ast.Name) and target.id == "fig" for target in targets
        )
    return exact_range and scatter_assigned_to_fig and fig_show


def notebook_executed_joblib_save_cell(content: str) -> bool:
    """Verify Task 08's marked cell performs the learner-owned exact save call."""

    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False
    marker = "# saving THE JOBLIB Model file"
    expected_path = "/opt/app-root/src/AI26X-apps/carido-model.joblib"
    for cell in document.get("cells", []) or []:
        if cell.get("cell_type") != "code" or cell.get("execution_count") is None:
            continue
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        if not text.lstrip().startswith(marker) or not re.search(
            r"(?m)^\s*%run\s+/opt/app-root/src/train_carido_model\.py\s*$", text
        ):
            continue
        if any(
            output.get("output_type") == "error" for output in (cell.get("outputs", []) or [])
        ):
            continue
        tree = _python_ast_for_notebook_cell(text)
        if tree is None:
            continue
        imports_joblib = any(
            isinstance(node, ast.Import)
            and any(alias.name == "joblib" and alias.asname in {None, "joblib"} for alias in node.names)
            for node in ast.walk(tree)
        )
        exact_dump = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "joblib"
            and node.func.attr == "dump"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "ml_model"
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == expected_path
            for node in ast.walk(tree)
        )
        if imports_joblib and exact_dump:
            return True
    return False


def notebook_executed_s3_transfer(
    content: str,
    method: str,
    object_key: str,
    *required_strings: str,
) -> bool:
    """Find an error-free executed boto3 transfer call for the exact object key."""

    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False
    for cell in document.get("cells", []) or []:
        if cell.get("cell_type") != "code" or cell.get("execution_count") is None:
            continue
        if any(
            output.get("output_type") == "error" for output in (cell.get("outputs", []) or [])
        ):
            continue
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        tree = _python_ast_for_notebook_cell(text)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == method
            ):
                continue
            arguments = list(node.args) + [keyword.value for keyword in node.keywords]
            literal_arguments = {
                str(argument.value)
                for argument in arguments
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            }
            if object_key in literal_arguments and all(
                required in literal_arguments for required in required_strings
            ):
                return True
    return False


def notebook_has_saved_output(content: str) -> bool:
    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False
    for cell in document.get("cells", []) or []:
        if cell.get("cell_type") != "code" or cell.get("execution_count") is None:
            continue
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        if not text.strip():
            continue
        outputs = cell.get("outputs", []) or []
        if outputs and not any(output.get("output_type") == "error" for output in outputs):
            return True
    return False


def notebook_cell_has_saved_output(content: str, markers: tuple[str, ...]) -> bool:
    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False
    for cell in document.get("cells", []) or []:
        if cell.get("cell_type") != "code" or cell.get("execution_count") is None:
            continue
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        if not all(marker in text for marker in markers):
            continue
        outputs = cell.get("outputs", []) or []
        return bool(outputs) and not any(
            output.get("output_type") == "error" for output in outputs
        )
    return False


def requirement_pinned(path: Path, package: str, version: str) -> bool:
    if not path.is_file():
        return False
    expected = f"{package.lower()}=={version}"
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        value = line.split("#", 1)[0].strip().lower().replace(" ", "")
        if value == expected:
            return True
    return False


def local_image_tags_same(images: tuple[str, ...]) -> bool:
    image_ids: list[str] = []
    for image in images:
        try:
            result = subprocess.run(
                ["podman", "image", "inspect", "--format", "{{.Id}}", image],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        image_id = result.stdout.strip()
        if result.returncode or not image_id:
            return False
        image_ids.append(image_id)
    return len(image_ids) == len(images) and len(set(image_ids)) == 1


def image_catalog_item(
    image_stream: dict[str, Any] | None,
    annotation_key: str,
    name: str,
    version: str,
) -> bool:
    for tag in dig(image_stream, "spec", "tags", default=[]) or []:
        raw = str(dig(tag, "annotations", annotation_key, default=""))
        try:
            dependencies = json.loads(raw)
        except json.JSONDecodeError:
            dependencies = []
        if any(
            str(item.get("name", "")).lower() == name.lower()
            and str(item.get("version", "")) == version
            for item in dependencies
            if isinstance(item, dict)
        ):
            return True
    return False


def image_dependency(image_stream: dict[str, Any] | None, name: str, version: str) -> bool:
    return image_catalog_item(
        image_stream,
        "opendatahub.io/notebook-python-dependencies",
        name,
        version,
    )


def image_software(image_stream: dict[str, Any] | None, name: str, version: str) -> bool:
    return image_catalog_item(
        image_stream,
        "opendatahub.io/notebook-software",
        name,
        version,
    )


def image_annotation_is(image_stream: dict[str, Any] | None, key: str, value: str) -> bool:
    candidates = [annotations(image_stream)]
    candidates.extend(
        dig(tag, "annotations", default={}) or {}
        for tag in (dig(image_stream, "spec", "tags", default=[]) or [])
    )
    return any(candidate.get(key) == value for candidate in candidates)


def dspa_ready(resource: dict[str, Any] | None) -> bool:
    if ready(resource):
        return True
    conditions = dig(resource, "status", "conditions", default=[]) or []
    required = {"APIServerReady", "PersistenceAgentReady", "ScheduledWorkflowReady"}
    truthy = {
        str(item.get("type"))
        for item in conditions
        if str(item.get("status", "")).lower() == "true"
    }
    return required <= truthy


def workflow_named(workflow: dict[str, Any], run_name: str) -> bool:
    def canonical(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")

    expected = canonical(run_name)
    metadata = workflow.get("metadata", {}) or {}
    values = [metadata.get("name", "")]
    values.extend(str(value) for value in (metadata.get("annotations", {}) or {}).values())
    values.extend(str(value) for value in (metadata.get("labels", {}) or {}).values())
    return any(
        canonical(value) == expected or canonical(value).startswith(f"{expected}-")
        for value in values
    )


def schedule_is_enabled_five_minutes(resource: dict[str, Any]) -> bool:
    enabled = dig(resource, "spec", "enabled", default=None)
    if enabled not in {True, "true", "True"}:
        return False
    interval = dig(resource, "spec", "trigger", "periodicSchedule", "intervalSecond")
    return str(interval) == "300"


def schedule_references_pipeline(resource: dict[str, Any], pipeline_name: str) -> bool:
    """Match the KFP ScheduledWorkflow pipeline-name field without substring guesses."""

    expected = re.sub(r"[^a-z0-9]+", "-", pipeline_name.lower()).strip("-")
    candidates = [
        dig(resource, "spec", "pipelineSpec", "pipelineName"),
        dig(resource, "spec", "pipelineSpec", "pipeline_name"),
        dig(resource, "spec", "pipelineName"),
        dig(resource, "spec", "pipeline_name"),
        annotations(resource).get("pipelines.kubeflow.org/pipeline-name"),
        labels(resource).get("pipelines.kubeflow.org/pipeline-name"),
    ]
    return any(
        re.sub(r"[^a-z0-9]+", "-", str(candidate).lower()).strip("-") == expected
        for candidate in candidates
        if candidate not in {None, ""}
    )


def workflow_links_to_schedule(workflow: dict[str, Any], schedule: dict[str, Any]) -> bool:
    if phase(workflow).lower() != "succeeded":
        return False
    schedule_name = resource_name(schedule)
    if schedule_name:
        completed = dig(
            schedule,
            "status",
            "workflowHistory",
            "completed",
            default=[],
        ) or []
        if any(item.get("name") == resource_name(workflow) for item in completed):
            return True
        for owner in dig(workflow, "metadata", "ownerReferences", default=[]) or []:
            if owner.get("name") == schedule_name:
                return True
        metadata = workflow.get("metadata", {}) or {}
        values = list((metadata.get("annotations", {}) or {}).values())
        values.extend((metadata.get("labels", {}) or {}).values())
        if any(str(value) == schedule_name for value in values):
            return True
    return False


def compiled_kfp_ir_matches(content: str, pipeline_name: str, sdk_version: str) -> bool:
    name_pattern = re.compile(
        rf"(?m)^\s*name:\s*['\"]?{re.escape(pipeline_name)}['\"]?\s*$"
    )
    sdk_pattern = re.compile(
        rf"(?m)^\s*sdkVersion:\s*['\"]?kfp-{re.escape(sdk_version)}['\"]?\s*$"
    )
    return bool(content.strip() and name_pattern.search(content) and sdk_pattern.search(content))


def read_text_if_file(path: str) -> str:
    candidate = Path(path)
    if not candidate.is_file():
        return ""
    return candidate.read_text(encoding="utf-8", errors="ignore")


def _canonical_kfp_task_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def _collect_kfp_task_dependencies(value: Any, result: set[str]) -> None:
    """Collect explicit and channel-implied dependencies from one KFP v2 task."""

    if isinstance(value, dict):
        for key, nested in value.items():
            if key == "producerTask" and isinstance(nested, str):
                result.add(_canonical_kfp_task_name(nested))
            elif key == "dependentTasks":
                if isinstance(nested, list):
                    result.update(
                        _canonical_kfp_task_name(item)
                        for item in nested
                        if isinstance(item, str)
                    )
                elif isinstance(nested, str):
                    result.add(_canonical_kfp_task_name(nested))
            _collect_kfp_task_dependencies(nested, result)
    elif isinstance(value, list):
        for nested in value:
            _collect_kfp_task_dependencies(nested, result)


def _kfp_root_task_dependencies_text(content: str) -> dict[str, set[str]]:
    """Parse the stable root DAG subset of KFP v2 YAML without PyYAML."""

    lines = content.splitlines()

    def key_line(index: int) -> tuple[int, str] | None:
        match = re.match(r"^(\s*)([A-Za-z0-9_.-]+):\s*(?:#.*)?$", lines[index])
        return (len(match.group(1)), match.group(2)) if match else None

    def block_end(start: int, indent: int, limit: int) -> int:
        for index in range(start + 1, limit):
            if not lines[index].strip() or lines[index].lstrip().startswith("#"):
                continue
            current_indent = len(lines[index]) - len(lines[index].lstrip())
            if current_indent <= indent:
                return index
        return limit

    def direct_child(
        key: str,
        parent_start: int,
        parent_indent: int,
        parent_end: int,
    ) -> tuple[int, int] | None:
        child_indent = parent_indent + 2
        for index in range(parent_start + 1, parent_end):
            if key_line(index) == (child_indent, key):
                return index, block_end(index, child_indent, parent_end)
        return None

    root = next(
        (
            (index, block_end(index, 0, len(lines)))
            for index in range(len(lines))
            if key_line(index) == (0, "root")
        ),
        None,
    )
    if root is None:
        return {}
    dag = direct_child("dag", root[0], 0, root[1])
    if dag is None:
        return {}
    tasks = direct_child("tasks", dag[0], 2, dag[1])
    if tasks is None:
        return {}

    headings = [
        (index, parsed[1])
        for index in range(tasks[0] + 1, tasks[1])
        if (parsed := key_line(index)) is not None and parsed[0] == 6
    ]
    result: dict[str, set[str]] = {}
    for heading_index, (start, task_name) in enumerate(headings):
        end = headings[heading_index + 1][0] if heading_index + 1 < len(headings) else tasks[1]
        dependencies: set[str] = set()
        dependent_indent: int | None = None
        for index in range(start + 1, end):
            line = lines[index]
            producer = re.match(
                r"^\s*producerTask:\s*['\"]?([^'\"\s#]+)['\"]?\s*(?:#.*)?$",
                line,
            )
            if producer:
                dependencies.add(_canonical_kfp_task_name(producer.group(1)))
            dependent = re.match(r"^(\s*)dependentTasks:\s*(.*?)\s*$", line)
            if dependent:
                dependent_indent = len(dependent.group(1))
                inline = dependent.group(2).strip()
                if inline.startswith("[") and inline.endswith("]"):
                    dependencies.update(
                        _canonical_kfp_task_name(item.strip(" '\""))
                        for item in inline[1:-1].split(",")
                        if item.strip(" '\"")
                    )
                continue
            if dependent_indent is not None:
                item = re.match(
                    r"^\s*-\s*['\"]?([^'\"\s#]+)['\"]?\s*(?:#.*)?$",
                    line,
                )
                if item:
                    dependencies.add(_canonical_kfp_task_name(item.group(1)))
                    continue
                if line.strip() and len(line) - len(line.lstrip()) <= dependent_indent:
                    dependent_indent = None
        canonical_name = _canonical_kfp_task_name(task_name)
        if not canonical_name or canonical_name in result:
            return {}
        result[canonical_name] = dependencies
    return result


def _kfp_root_task_dependencies(content: str) -> dict[str, set[str]]:
    """Return root DAG task dependencies from a compiled KFP v2 IR document."""

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return _kfp_root_task_dependencies_text(content)
    try:
        document = yaml.safe_load(content)
    except yaml.YAMLError:
        return _kfp_root_task_dependencies_text(content)
    if not isinstance(document, dict):
        return {}
    root_tasks = dig(document, "root", "dag", "tasks", default={})
    if not isinstance(root_tasks, dict):
        return {}

    result: dict[str, set[str]] = {}
    for task_key, task_spec in root_tasks.items():
        if not isinstance(task_spec, dict):
            return {}
        task_name = dig(task_spec, "taskInfo", "name", default=task_key)
        canonical_name = _canonical_kfp_task_name(task_name)
        if not canonical_name or canonical_name in result:
            return {}
        dependencies: set[str] = set()
        _collect_kfp_task_dependencies(task_spec, dependencies)
        result[canonical_name] = dependencies
    return result


def compiled_pipeline_has_ordered_chain(content: str, component_names: list[str]) -> bool:
    """Verify the required KFP v2 root tasks form the requested ordered chain.

    KFP records ordering either in ``dependentTasks`` (for ``.after()``) or in
    input channels via ``producerTask``. Every stage after the first must
    consume or depend on its immediate predecessor, and no stage may depend on
    itself or a later required stage.
    """

    expected = [_canonical_kfp_task_name(name) for name in component_names]
    if len(expected) != len(set(expected)) or any(not name for name in expected):
        return False
    task_dependencies = _kfp_root_task_dependencies(content)
    if not all(name in task_dependencies for name in expected):
        return False

    positions = {name: index for index, name in enumerate(expected)}
    for index, name in enumerate(expected):
        required_dependencies = {
            dependency
            for dependency in task_dependencies[name]
            if dependency in positions
        }
        if any(positions[dependency] >= index for dependency in required_dependencies):
            return False
        if index and expected[index - 1] not in required_dependencies:
            return False
    return True


def workflow_stages_succeeded(workflow: dict[str, Any], stage_names: list[str]) -> bool:
    nodes = dig(workflow, "status", "nodes", default={}) or {}
    if not isinstance(nodes, dict):
        return False

    def canonical(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")

    succeeded: set[str] = set()
    expected = {canonical(name) for name in stage_names}
    for node in nodes.values():
        if str(node.get("phase", "")).lower() != "succeeded":
            continue
        candidates = {
            canonical(node.get("displayName", "")),
            canonical(node.get("name", "")),
            canonical(node.get("templateName", "")),
        }
        for stage in expected:
            if any(value == stage or value.startswith(f"{stage}-") for value in candidates):
                succeeded.add(stage)
    return succeeded == expected


def s3_fixture_object_exists(bucket: str, key: str) -> bool:
    helper = ROOT / "tasks" / "common" / "s3_fixture.py"
    if not helper.is_file() or not key:
        return False
    try:
        helper_module = runpy.run_path(str(helper), run_name="ai267_s3_fixture")
        status, body = helper_module["signed_request"]("GET", bucket, key)
    except (Exception, SystemExit):
        return False
    return status == 200 and bool(body)


def serving_runtime_is_openvino_onnx(
    oc: Any,
    namespace: str,
    runtime_name: str,
) -> bool:
    if not runtime_name:
        return False
    runtime = oc.get(
        "servingruntime.serving.kserve.io",
        runtime_name,
        namespace,
    )
    formats = dig(runtime, "spec", "supportedModelFormats", default=[]) or []
    onnx_v1 = any(
        str(item.get("name", "")).lower() == "onnx"
        and str(item.get("version", "")) == "1"
        for item in formats
        if isinstance(item, dict)
    )
    identity = " ".join(
        (
            resource_name(runtime),
            json.dumps(annotations(runtime), ensure_ascii=False),
            json.dumps(
                dig(runtime, "spec", "annotations", default={}) or {},
                ensure_ascii=False,
            ),
            json.dumps(
                dig(runtime, "spec", "containers", default=[]) or [],
                ensure_ascii=False,
            ),
        )
    ).lower()
    openvino = "openvino" in identity or bool(
        re.search(r"(?:^|[^a-z0-9])ovms(?:[^a-z0-9]|$)", identity)
    )
    return onnx_v1 and openvino


def pod_resource_ready(resource: dict[str, Any] | None) -> bool:
    statuses = dig(resource, "status", "containerStatuses", default=[]) or []
    return phase(resource) == "Running" and bool(statuses) and all(bool(item.get("ready")) for item in statuses)


def pipeline_server_pods_ready(oc: Any, namespace: str) -> bool:
    groups = {
        "api": ("ds-pipeline-dspa-", "api-server"),
        "persistence": ("ds-pipeline-persistenceagent-", "persistenceagent"),
        "scheduler": ("ds-pipeline-scheduledworkflow-", "scheduledworkflow"),
    }
    matched: dict[str, list[dict[str, Any]]] = {name: [] for name in groups}
    for pod in oc.list("pod", namespace):
        name = resource_name(pod).lower()
        for group, tokens in groups.items():
            if any(token in name for token in tokens):
                matched[group].append(pod)
    return all(items and any(pod_resource_ready(item) for item in items) for items in matched.values())


def unauthenticated_v2_inference_ok(host: str, model_name: str) -> bool:
    if not host or not re.fullmatch(r"[A-Za-z0-9.-]+(?::[0-9]+)?", host):
        return False
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        metadata_request = urllib.request.Request(
            f"https://{host}/v2/models/{model_name}",
            method="GET",
        )
        with urllib.request.urlopen(metadata_request, context=context, timeout=20) as response:
            metadata = json.loads(response.read())
        inputs = metadata.get("inputs", []) or []
        if not any(
            item.get("name") == "float_input"
            and str(item.get("datatype", "")).upper() == "FP32"
            and item.get("shape") == [-1, 5]
            for item in inputs
            if isinstance(item, dict)
        ):
            return False
    except (json.JSONDecodeError, OSError, urllib.error.URLError, ValueError):
        return False

    payload = json.dumps(
        {
            "inputs": [
                {
                    "name": "float_input",
                    "shape": [1, 5],
                    "datatype": "FP32",
                    "data": [[0.2, -0.1, 0.5, 1.0, -0.4]],
                }
            ]
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://{host}/v2/models/{model_name}/infer",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, context=context, timeout=20) as response:
            body = response.read()
            return response.status == 200 and bool(body)
    except (OSError, urllib.error.URLError, ValueError):
        return False


def git_check(oc: Any, namespace: str, notebook: str, expression: str) -> bool:
    return exec_ok(
        oc,
        namespace,
        notebook,
        ["bash", "-lc", f"test -d /opt/app-root/src/AI26X-apps/.git && {expression}"],
    )


def notebook_is_stopped(oc: Any, namespace: str, notebook_name: str) -> bool:
    notebook = oc.get("notebook.kubeflow.org", notebook_name, namespace)
    return (
        notebook is not None
        and "kubeflow-resource-stopped" in annotations(notebook)
        and notebook_pod(oc, namespace, notebook_name) is None
    )


def stopped_notebook_repo_checks(
    oc: Any,
    namespace: str,
    notebook: dict[str, Any] | None,
) -> tuple[bool, bool, bool]:
    """Inspect a stopped workbench PVC read-only and remove all verifier resources."""

    if not notebook or not hasattr(oc, "run_input"):
        return False, False, False
    pod_spec = dig(notebook, "spec", "template", "spec", default={}) or {}
    container = first_container(notebook)
    image = str(container.get("image", ""))
    volume_by_name = {
        str(volume.get("name", "")): volume
        for volume in (pod_spec.get("volumes", []) or [])
        if isinstance(volume, dict)
    }
    workspace_volume = next(
        (
            volume_by_name.get(str(mount.get("name", "")))
            for mount in (container.get("volumeMounts", []) or [])
            if mount.get("mountPath") == "/opt/app-root/src"
        ),
        None,
    )
    if not workspace_volume:
        workspace_volume = next(
            (
                volume
                for volume in volume_by_name.values()
                if dig(volume, "persistentVolumeClaim", "claimName")
            ),
            None,
        )
    claim = str(dig(workspace_volume, "persistentVolumeClaim", "claimName", default=""))
    if not image or not claim:
        return False, False, False

    verify_code = r'''
import json
import pathlib
import subprocess

repo = pathlib.Path("/workspace/AI26X-apps")
safe = f"safe.directory={repo}"
def git(*args):
    result = subprocess.run(
        ["git", "-c", safe, "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""

remote = git("remote", "get-url", "origin")
print(json.dumps({
    "repository": remote in {
        "https://github.com/RedHatTraining/AI26X-apps",
        "https://github.com/RedHatTraining/AI26X-apps.git",
    },
    "branch": git("branch", "--show-current") == "RHOAI3.3",
    "file": (repo / "workbench/working/train_model.ipynb").is_file(),
}, sort_keys=True))
'''
    job_name = f"ai267-grade-05-{secrets.token_hex(4)}"
    manifest = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": namespace,
            "labels": {"ai267.practice/created-by": "task-05-grader"},
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 180,
            "ttlSecondsAfterFinished": 300,
            "template": {
                "metadata": {
                    "labels": {"ai267.practice/created-by": "task-05-grader"},
                },
                "spec": {
                    "restartPolicy": "Never",
                    "automountServiceAccountToken": False,
                    "containers": [
                        {
                            "name": "verify",
                            "image": image,
                            "command": ["python3", "-c", verify_code],
                            "env": [{"name": "HOME", "value": "/tmp"}],
                            "volumeMounts": [
                                {
                                    "name": "workspace",
                                    "mountPath": "/workspace",
                                    "readOnly": True,
                                }
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "name": "workspace",
                            "persistentVolumeClaim": {
                                "claimName": claim,
                                "readOnly": True,
                            },
                        }
                    ],
                },
            },
        },
    }
    image_pull_secrets = [
        {"name": str(item.get("name"))}
        for item in (pod_spec.get("imagePullSecrets", []) or [])
        if isinstance(item, dict) and item.get("name")
    ]
    if image_pull_secrets:
        manifest["spec"]["template"]["spec"]["imagePullSecrets"] = image_pull_secrets
    checks = (False, False, False)
    cleanup_ok = True
    create_attempted = False
    try:
        create_attempted = True
        created = oc.run_input(
            json.dumps(manifest),
            "create",
            "-f",
            "-",
            "-o",
            "json",
            timeout=30,
        )
        if created.returncode:
            return checks
        waited = oc.run(
            "wait",
            "--for=condition=complete",
            f"job/{job_name}",
            "-n",
            namespace,
            "--timeout=150s",
            timeout=165,
        )
        if waited.returncode:
            return checks
        logs = oc.run("logs", f"job/{job_name}", "-n", namespace, timeout=30)
        if logs.returncode:
            return checks
        lines = [line for line in logs.stdout.splitlines() if line.strip()]
        evidence = json.loads(lines[-1]) if lines else {}
        checks = (
            evidence.get("repository") is True,
            evidence.get("branch") is True,
            evidence.get("file") is True,
        )
    except (AttributeError, json.JSONDecodeError, TypeError, ValueError):
        checks = (False, False, False)
    finally:
        if create_attempted:
            existing = oc.run(
                "get",
                "job",
                job_name,
                "-n",
                namespace,
                "-o",
                "json",
                timeout=20,
            )
            if existing.returncode:
                cleanup_ok = "notfound" in existing.stderr.lower().replace(" ", "")
            else:
                try:
                    owned = (
                        dig(
                            json.loads(existing.stdout),
                            "metadata",
                            "labels",
                            "ai267.practice/created-by",
                        )
                        == "task-05-grader"
                    )
                except (json.JSONDecodeError, TypeError):
                    owned = False
                if not owned:
                    cleanup_ok = False
                else:
                    deleted = oc.run(
                        "delete",
                        "job",
                        job_name,
                        "-n",
                        namespace,
                        "--wait=true",
                        "--timeout=60s",
                        timeout=75,
                    )
                    cleanup_ok = deleted.returncode == 0 or (
                        "notfound" in deleted.stderr.lower().replace(" ", "")
                    )
    return tuple(value and cleanup_ok for value in checks)


def s3_object(
    oc: Any,
    namespace: str,
    notebook: str,
    key: str,
    expected_text: str | None = None,
) -> bool:
    code = r'''
import os, sys
import boto3
endpoint = os.environ.get("AWS_S3_ENDPOINT") or os.environ.get("AWS_ENDPOINT_URL")
bucket = os.environ.get("AWS_S3_BUCKET") or os.environ.get("AWS_BUCKET")
client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    verify=False,
)
body = client.get_object(Bucket=bucket, Key=sys.argv[1])["Body"].read()
if not body:
    raise SystemExit(2)
if len(sys.argv) > 2 and body.decode("utf-8").strip() != sys.argv[2]:
    raise SystemExit(3)
print(len(body))
'''
    command = ["python3", "-c", code, key]
    if expected_text is not None:
        command.append(expected_text)
    return exec_ok(oc, namespace, notebook, command, timeout=60)


def s3_connection_matches(
    secret: dict[str, Any] | None,
    *,
    access_key: str,
    secret_key: str,
    endpoint: str,
    region: str,
    bucket: str,
) -> bool:
    data = secret_data(secret)
    return (
        annotations(secret).get("opendatahub.io/connection-type-protocol") == "s3"
        and data.get("AWS_ACCESS_KEY_ID") == access_key
        and data.get("AWS_SECRET_ACCESS_KEY") == secret_key
        and data.get("AWS_DEFAULT_REGION") == region
        and data.get("AWS_S3_BUCKET") == bucket
        and str(data.get("AWS_S3_ENDPOINT", "")).rstrip("/") == endpoint.rstrip("/")
    )


def s3_object_matches_local(
    oc: Any,
    namespace: str,
    notebook: str,
    local_path: str,
    key: str,
    downloaded_path: str | None = None,
) -> bool:
    code = r'''
import hashlib, os, pathlib, sys
import boto3
path = pathlib.Path(sys.argv[1])
if not path.is_file() or path.stat().st_size == 0:
    raise SystemExit(2)
endpoint = os.environ.get("AWS_S3_ENDPOINT") or os.environ.get("AWS_ENDPOINT_URL")
bucket = os.environ.get("AWS_S3_BUCKET") or os.environ.get("AWS_BUCKET")
client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    verify=False,
)
remote = client.get_object(Bucket=bucket, Key=sys.argv[2])["Body"].read()
if not remote or hashlib.sha256(remote).digest() != hashlib.sha256(path.read_bytes()).digest():
    raise SystemExit(3)
if len(sys.argv) > 3:
    downloaded = pathlib.Path(sys.argv[3])
    if not downloaded.is_file() or downloaded.stat().st_size == 0:
        raise SystemExit(4)
    if hashlib.sha256(downloaded.read_bytes()).digest() != hashlib.sha256(path.read_bytes()).digest():
        raise SystemExit(5)
'''
    command = ["python3", "-c", code, local_path, key]
    if downloaded_path is not None:
        command.append(downloaded_path)
    return exec_ok(
        oc,
        namespace,
        notebook,
        command,
        timeout=60,
    )


def s3_prefix_has(oc: Any, namespace: str, notebook: str, names: list[str]) -> bool:
    code = r'''
import os, sys
import boto3
endpoint = os.environ.get("AWS_S3_ENDPOINT") or os.environ.get("AWS_ENDPOINT_URL")
bucket = os.environ.get("AWS_S3_BUCKET") or os.environ.get("AWS_BUCKET")
client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    verify=False,
)
keys = []
for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="issues_prediction-"):
    keys.extend(item["Key"] for item in page.get("Contents", []))
expected = set(sys.argv[1:])
folders = {}
for key in keys:
    if "/" not in key:
        continue
    folder, name = key.split("/", 1)
    if not folder.startswith("issues_prediction-") or "/" in name:
        continue
    folders.setdefault(folder, set()).add(name)
if not any(expected <= found for found in folders.values()):
    raise SystemExit(2)
print("\n".join(keys))
'''
    return exec_ok(oc, namespace, notebook, ["python3", "-c", code, *names], timeout=60)


def local_joblib_model_ok(oc: Any, namespace: str, notebook: str, path: str) -> bool:
    code = r'''
import pathlib, sys
import joblib
path = pathlib.Path(sys.argv[1])
if not path.is_file() or path.stat().st_size == 0:
    raise SystemExit(2)
model = joblib.load(path)
if int(getattr(model, "n_features_in_", -1)) != 8:
    raise SystemExit(3)
if not callable(getattr(model, "predict", None)):
    raise SystemExit(4)
'''
    return exec_ok(oc, namespace, notebook, ["python3", "-c", code, path])


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_dicts(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_dicts(nested)


def elyra_pipeline_checks(content: str) -> tuple[bool, bool]:
    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False, False
    pipelines = document.get("pipelines", []) or []
    if not pipelines or not isinstance(pipelines[0], dict):
        return False, False
    pipeline = pipelines[0]
    nodes = pipeline.get("nodes", []) or []
    expected = [
        ("data_ingestion.py", "data.csv"),
        ("data_preprocessing.py", "clean-data.csv"),
        ("data_training_and_forecasting.py", "forecast-data.csv"),
    ]
    if len(nodes) != len(expected) or not all(isinstance(node, dict) for node in nodes):
        return False, False

    node_by_script: dict[str, dict[str, Any]] = {}
    for node in nodes:
        filename = str(
            dig(node, "app_data", "component_parameters", "filename", default="")
        )
        script = filename.replace("\\", "/").rsplit("/", 1)[-1]
        if script not in {name for name, _ in expected} or script in node_by_script:
            return False, False
        node_by_script[script] = node
    if set(node_by_script) != {script for script, _ in expected}:
        return False, False

    runtime = str(dig(pipeline, "app_data", "properties", "runtime", default=""))
    outputs_ok = all(
        dig(
            node_by_script[script],
            "app_data",
            "component_parameters",
            "outputs",
            default=[],
        )
        == [output]
        for script, output in expected
    )
    nodes_ok = runtime == "Pipelines"

    node_ids = {
        script: str(node_by_script[script].get("id", ""))
        for script, _ in expected
    }
    if not all(node_ids.values()) or len(set(node_ids.values())) != len(node_ids):
        return False, outputs_ok

    edges: set[tuple[str, str]] = set()
    ids = set(node_ids.values())
    for script, node in node_by_script.items():
        source = node_ids[script]
        for entry in _walk_dicts(node.get("outputs", [])):
            for key, value in entry.items():
                if "node" in str(key).lower() and str(value) in ids and str(value) != source:
                    edges.add((source, str(value)))
        for entry in _walk_dicts(node.get("inputs", [])):
            for key, value in entry.items():
                if "node" in str(key).lower() and str(value) in ids and str(value) != source:
                    edges.add((str(value), source))
    for entry in _walk_dicts({key: value for key, value in pipeline.items() if key != "nodes"}):
        source = next(
            (str(value) for key, value in entry.items() if any(token in str(key).lower() for token in ("source", "from")) and str(value) in ids),
            "",
        )
        target = next(
            (str(value) for key, value in entry.items() if any(token in str(key).lower() for token in ("target", "to")) and str(value) in ids),
            "",
        )
        if source and target and source != target:
            edges.add((source, target))

    ordered_ids = [node_ids[script] for script, _ in expected]
    nodes_ok = nodes_ok and all(
        (source, target) in edges
        for source, target in zip(ordered_ids, ordered_ids[1:])
    )
    return nodes_ok, outputs_ok


def elyra_pipeline_settings_ok(content: str) -> bool:
    try:
        document = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False
    pipeline = next(
        (item for item in (document.get("pipelines", []) or []) if isinstance(item, dict)),
        None,
    )
    if pipeline is None:
        return False
    properties = dig(pipeline, "app_data", "properties", default={}) or {}
    defaults = properties.get("pipeline_defaults", {}) or {}
    mappings = defaults.get("kubernetes_secrets", []) or []
    expected = {
        (key, "aws-connection-s3-minio", key)
        for key in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_S3_ENDPOINT",
            "AWS_S3_BUCKET",
        )
    }
    actual = {
        (
            str(item.get("env_var", "")),
            str(item.get("name", "")),
            str(item.get("key", "")),
        )
        for item in mappings
        if isinstance(item, dict)
    }
    return (
        properties.get("runtime") == "Pipelines"
        and defaults.get("runtime_image") == ELYRA_RUNTIME_IMAGE
        and len(mappings) == 4
        and actual == expected
    )


def elyra_runtime_image_metadata_ok(oc: Any, namespace: str, notebook: str) -> bool:
    code = r'''
import json
import pathlib
import subprocess

roots = [pathlib.Path.home() / ".local/share/jupyter/metadata/runtime-images"]
result = subprocess.run(["jupyter", "--data-dir"], capture_output=True, text=True)
if result.returncode == 0 and result.stdout.strip():
    roots.append(pathlib.Path(result.stdout.strip()) / "metadata/runtime-images")
for root in roots:
    for path in root.glob("*.json"):
        try:
            document = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if (
            document.get("display_name") == "__ELYRA_RUNTIME_DISPLAY_NAME__"
            and (document.get("metadata") or {}).get("image_name")
            == "__ELYRA_RUNTIME_IMAGE__"
        ):
            raise SystemExit(0)
raise SystemExit(2)
'''.replace("__ELYRA_RUNTIME_DISPLAY_NAME__", ELYRA_RUNTIME_DISPLAY_NAME).replace(
        "__ELYRA_RUNTIME_IMAGE__", ELYRA_RUNTIME_IMAGE
    )
    return exec_ok(oc, namespace, notebook, ["python3", "-c", code])


def profile_identifiers(profile: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("identifier")): item
        for item in (dig(profile, "spec", "identifiers", default=[]) or [])
    }


def profile_matches(
    profile: dict[str, Any] | None,
    cpu: tuple[str, str, str],
    memory: tuple[str, str, str],
) -> bool:
    identifiers = profile_identifiers(profile)
    cpu_item = identifiers.get("cpu", {})
    memory_item = identifiers.get("memory", {})
    return (
        tuple(str(cpu_item.get(key, "")) for key in ("minCount", "defaultCount", "maxCount")) == cpu
        and tuple(str(memory_item.get(key, "")) for key in ("minCount", "defaultCount", "maxCount")) == memory
    )


def workflows(oc: Any, namespace: str) -> list[dict[str, Any]]:
    return oc.list("workflow.argoproj.io", namespace)


def grader_01(oc: Any, ns: str) -> list[Check]:
    project = oc.get("namespace", "my-lab-pro")
    notebook = oc.get("notebook.kubeflow.org", "myworkbench-wb", ns)
    profile_namespace = "redhat-ods-applications"
    profile = oc.get(
        "hardwareprofile.infrastructure.opendatahub.io",
        "task01-2cpu-8gi",
        profile_namespace,
    )
    container = first_container(notebook)
    resources = container.get("resources", {}) or {}
    requests = resources.get("requests", {}) or {}
    limits = resources.get("limits", {}) or {}
    rajan_roles = roles_for_user(oc, ns, "rajan")
    punit_roles = roles_for_user(oc, ns, "punit")
    suraj_roles = roles_for_user(oc, ns, "suraj")
    role_ok = (
        "admin" in rajan_roles
        and "admin" in punit_roles
        and "edit" in suraj_roles
        and not ({"admin", "cluster-admin"} & suraj_roles)
        and not dangerous_cluster_binding(oc, users={"rajan", "punit", "suraj"})
    )
    resource_ok = (
        ns == "my-lab-pro"
        and resource_name(project) == "my-lab-pro"
        and notebook_image_is(
            notebook,
            display_name="Jupyter | PyTorch | CUDA | Python 3.12",
            image_tokens=("pytorch",),
        )
        and notebook_image_version_is(notebook, "2025.2")
        and annotations(profile).get("opendatahub.io/display-name")
        == "Task 01 - 2 CPU, 8 GiB"
        and profile_matches(profile, ("2", "2", "2"), ("8Gi", "8Gi", "8Gi"))
        and notebook_uses_hardware_profile(
            notebook,
            "task01-2cpu-8gi",
            profile_namespace,
        )
        and str(requests.get("cpu")) in {"2", "2000m"}
        and str(limits.get("cpu")) in {"2", "2000m"}
        and str(requests.get("memory")) in {"8Gi", "8192Mi"}
        and str(limits.get("memory")) in {"8Gi", "8192Mi"}
    )
    pvc = oc.get("pvc", "myworkbench-wb-storage", ns)
    storage = str(dig(pvc, "spec", "resources", "requests", "storage", default=""))
    pvc_ok = (
        storage in {"2Gi", "2048Mi"}
        and phase(pvc) == "Bound"
        and notebook_has_pvc(notebook, "myworkbench-wb-storage")
    )
    configmap = oc.get("configmap", "myworkbench-env", ns)
    env_ok = (
        dig(configmap, "data", "var") == "devops-wala"
        and notebook_has_source(notebook, "configMap", "myworkbench-env")
    )
    repo_ok = git_check(
        oc,
        ns,
        "myworkbench-wb",
        "url=$(git -C /opt/app-root/src/AI26X-apps remote get-url origin) && "
        "{ test \"$url\" = https://github.com/RedHatTraining/AI26X-apps.git || "
        "test \"$url\" = https://github.com/RedHatTraining/AI26X-apps; }",
    )
    return [
        check("01-rbac", "프로젝트 Admin/Contributor 권한", role_ok, "rajan·punit=admin, suraj=edit RoleBinding"),
        check(
            "01-workbench",
            "my-lab-pro PyTorch 2025.2 Workbench와 2 CPU/8 GiB",
            resource_ok,
            "PyTorch 2.7/Python 3.12 image version 2025.2 and global task01-2cpu-8gi profile",
        ),
        check("01-storage", "2 GiB 영구 스토리지", pvc_ok, "myworkbench-wb-storage Bound 및 mount"),
        check("01-env", "ConfigMap 환경 변수", env_ok, "myworkbench-env: var=devops-wala"),
        check("01-git", "AI26X-apps 복제", repo_ok, "Workbench PVC의 Git 저장소"),
    ]


def grader_02(oc: Any, ns: str) -> list[Check]:
    dev_group = oc.get("group.user.openshift.io", "devops-wala")
    admin_group = oc.get("group.user.openshift.io", "ai267-admins")
    auth = oc.get("auth.services.platform.opendatahub.io", "auth")
    allowed = set(dig(auth, "spec", "allowedGroups", default=[]) or [])
    admins = set(dig(auth, "spec", "adminGroups", default=[]) or [])
    dev_users = {"developer", "rajan", "punit"}
    other_group_member = any(
        resource_name(group) != "devops-wala" and bool(group_users(group) & dev_users)
        for group in oc.list("group.user.openshift.io")
    )
    membership_ok = (
        dev_group is not None
        and group_users(dev_group) == dev_users
        and not (group_users(admin_group) & dev_users)
        and not other_group_member
        and not dangerous_cluster_binding(
            oc,
            users=dev_users,
            groups={"devops-wala", "system:authenticated", "system:authenticated:oauth"},
        )
    )
    return [
        check("02-users", "일반 사용자 그룹 구성", group_users(dev_group) == dev_users, "devops-wala exact membership"),
        check("02-admins", "관리자 그룹 구성", group_users(admin_group) == {"suraj", "raja", "andrew"}, "ai267-admins exact membership"),
        check("02-auth", "Auth allowed/admin groups", allowed == {"devops-wala"} and admins == {"ai267-admins"}, "Auth/auth spec"),
        check("02-isolation", "일반 사용자 그룹 격리", membership_ok, "다른 Group/관리자 ClusterRoleBinding에서 제외"),
        check(
            "02-no-broad-admin",
            "일반 그룹 관리자 권한 차단",
            auth is not None
            and dev_group is not None
            and not dangerous_cluster_binding(
                oc,
                users=dev_users,
                groups={"devops-wala", "system:authenticated", "system:authenticated:oauth"},
            )
            and "system:authenticated" not in allowed
            and "system:authenticated:oauth" not in allowed,
            "broad access/admin binding 없음",
        ),
    ]


def grader_03(oc: Any, ns: str) -> list[Check]:
    large = oc.get("hardwareprofile.infrastructure.opendatahub.io", "large", ns)
    xlarge = oc.get("hardwareprofile.infrastructure.opendatahub.io", "xlarge", ns)
    hidden = all(
        item is None or annotations(item).get("opendatahub.io/disabled") == "true"
        for item in (large, xlarge)
    )
    medium = oc.get("hardwareprofile.infrastructure.opendatahub.io", "medium-small", ns)
    my_medium = oc.get("hardwareprofile.infrastructure.opendatahub.io", "my-medium", ns)
    profiles_ok = (
        hidden
        and annotations(medium).get("opendatahub.io/display-name") == "MediumSmall"
        and profile_matches(medium, ("1", "1", "2"), ("16Gi", "16Gi", "16Gi"))
        and annotations(my_medium).get("opendatahub.io/display-name") == "My-medium"
        and profile_matches(my_medium, ("1", "1", "2"), ("1Gi", "1Gi", "2Gi"))
    )
    notebook = oc.get("notebook.kubeflow.org", "manage-resources-wb", ns)
    note = annotations(notebook)
    selected_profile_name = str(note.get("opendatahub.io/hardware-profile-name", ""))
    selected_profile_namespace = str(
        note.get("opendatahub.io/hardware-profile-namespace", "") or ns
    )
    selected_profile = oc.get(
        "hardwareprofile.infrastructure.opendatahub.io",
        selected_profile_name,
        selected_profile_namespace,
    )
    selected_profile_display = str(
        annotations(selected_profile).get("opendatahub.io/display-name", "")
    ).strip()
    small_profile = selected_profile is not None and selected_profile_display.casefold() == "small"
    notebook_ok = (
        notebook_image_is(
            notebook,
            display_name="Jupyter | Data Science | CPU | Python 3.12",
            image_tokens=("generic-data-science",),
        )
        and small_profile
        and pod_is_ready(oc, ns, "manage-resources-wb")
    )
    repo_ok = git_check(
        oc,
        ns,
        "manage-resources-wb",
        "url=$(git -C /opt/app-root/src/AI26X-apps remote get-url origin) && "
        "{ test \"$url\" = https://github.com/RedHatTraining/AI26X-apps.git || "
        "test \"$url\" = https://github.com/RedHatTraining/AI26X-apps; } && "
        "test \"$(git -C /opt/app-root/src/AI26X-apps branch --show-current)\" = RHOAI3.3",
    )
    notebook_file = exec_stdout(
        oc,
        ns,
        "manage-resources-wb",
        [
            "git",
            "-C",
            "/opt/app-root/src/AI26X-apps",
            "show",
            "experiment:workbench/working/experiment1.ipynb",
        ],
    )
    code = notebook_code(notebook_file)
    plot_ok = (
        bool(re.search(r"(?:import\s+numpy|from\s+numpy\s+import)", code))
        and bool(re.search(r"(?:import\s+plotly\.express|from\s+plotly\s+import\s+express)", code))
        and notebook_has_exact_scatter_plot(notebook_file)
        and bool(
            re.search(r"\bx\s*\*\*\s*2\b", code)
            or re.search(r"np\.(?:square|power)\s*\(\s*x(?:\s*,\s*2)?\s*\)", code)
        )
        and notebook_cell_executed(notebook_file, "scatter")
        and notebook_cell_executed(notebook_file, "fig.show")
        and notebook_has_saved_output(notebook_file)
    )
    merge_ok = git_check(
        oc,
        ns,
        "manage-resources-wb",
        "git -C /opt/app-root/src/AI26X-apps show-ref --verify --quiet refs/heads/experiment && "
        "git -C /opt/app-root/src/AI26X-apps show-ref --verify --quiet refs/remotes/origin/RHOAI3.3 && "
        "git -C /opt/app-root/src/AI26X-apps cat-file -e experiment:workbench/working/experiment1.ipynb && "
        "! git -C /opt/app-root/src/AI26X-apps diff --quiet origin/RHOAI3.3..experiment -- workbench/working/experiment1.ipynb && "
        "git -C /opt/app-root/src/AI26X-apps merge-base --is-ancestor experiment RHOAI3.3 && "
        "test \"$(git -C /opt/app-root/src/AI26X-apps rev-list --count origin/RHOAI3.3..experiment)\" -ge 1 && "
        "test -z \"$(git -C /opt/app-root/src/AI26X-apps status --porcelain)\"",
    )
    return [
        check("03-profiles", "Hardware Profile 구성", profiles_ok, "Large/X Large 숨김, MediumSmall/My-medium 값"),
        check("03-workbench", "Small Data Science Workbench", notebook_ok, "manage-resources-wb uses an available Small profile"),
        check("03-repository", "RHOAI3.3 저장소", repo_ok, "AI26X-apps local branch"),
        check("03-notebook", "experiment1 산점도", plot_ok, "NumPy·Plotly notebook 내용"),
        check("03-merge", "feature branch 병합", merge_ok, "experiment → RHOAI3.3, clean worktree"),
    ]


def grader_04(oc: Any, ns: str) -> list[Check]:
    target_ns = "projects-data"
    secret = oc.get("secret", "projects-data-connection", target_ns)
    if secret is None:
        secret = oc.get(
            "secret",
            "aws-connection-projects-data-connection",
            target_ns,
        )
    secret_ok = s3_connection_matches(
        secret,
        access_key="minio",
        secret_key="minio123",
        endpoint="https://minio-api-minio.apps.lab.example.com",
        region="us-east-1",
        bucket="projects-data-bucket",
    )
    notebook = oc.get("notebook.kubeflow.org", "projects-data-wb", target_ns)
    workbench_ok = (
        notebook_image_is(
            notebook,
            display_name="Jupyter | Data Science | CPU | Python 3.12",
            image_tokens=("generic-data-science",),
        )
        and notebook_has_connection(notebook, target_ns, "projects-data-connection")
        and pod_is_ready(oc, target_ns, "projects-data-wb")
    )
    repo = "/opt/app-root/src/AI26X-apps"
    repository_ok = git_check(
        oc,
        target_ns,
        "projects-data-wb",
        f"url=$(git -C {repo} remote get-url origin) && "
        "{ test \"$url\" = https://github.com/RedHatTraining/AI26X-apps.git || "
        "test \"$url\" = https://github.com/RedHatTraining/AI26X-apps; } && "
        f"test \"$(git -C {repo} branch --show-current)\" = RHOAI3.3 && "
        f"test -f {repo}/workbench/connections/workbench-connections.ipynb",
    )
    source = f"{repo}/workbench/connections/dataset.csv"
    downloaded = f"{repo}/workbench/connections/downloaded-dataset.csv"
    notebook_content = exec_stdout(
        oc,
        target_ns,
        "projects-data-wb",
        ["cat", f"{repo}/workbench/connections/workbench-connections.ipynb"],
    )
    notebook_execution_ok = notebook_cell_executed(
        notebook_content, "upload_file"
    ) and notebook_cell_executed(notebook_content, "download_file")
    local_ok = exec_ok(
        oc,
        target_ns,
        "projects-data-wb",
        ["bash", "-lc", f"test -s {source} && test -s {downloaded} && cmp -s {source} {downloaded}"],
    )
    object_ok = s3_object_matches_local(
        oc,
        target_ns,
        "projects-data-wb",
        source,
        "dataset.csv",
    )
    return [
        check("04-connection", "S3 Connection", secret_ok, "projects-data-connection exact credentials/bucket"),
        check("04-workbench", "Data Science Workbench", workbench_ok, "projects-data-wb Ready with connection"),
        check("04-repository", "AI26X-apps RHOAI3.3", repository_ok, "exact remote/branch/notebook"),
        check(
            "04-download",
            "Notebook upload/download와 byte 비교",
            notebook_execution_ok and local_ok,
            "saved execution plus dataset.csv equals downloaded-dataset.csv",
        ),
        check("04-object", "S3 root dataset", object_ok, "projects-data-bucket/dataset.csv matches local"),
    ]


def grader_05(oc: Any, ns: str) -> list[Check]:
    notebook = oc.get("notebook.kubeflow.org", "model-training", ns)
    image_ok = notebook_image_is(
        notebook,
        display_name="Jupyter | PyTorch | CUDA | Python 3.12",
        image_tokens=("pytorch",),
    )
    configmap = oc.get("configmap", "model-training-env", ns)
    env_ok = (
        dig(configmap, "data", "RANDOM_SIZE") == "40"
        and notebook_has_source(notebook, "configMap", "model-training-env")
    )
    stopped_ok = notebook_is_stopped(oc, ns, "model-training")
    repo_ok, branch_ok, file_ok = (
        stopped_notebook_repo_checks(oc, ns, notebook)
        if stopped_ok
        else (False, False, False)
    )
    return [
        check("05-image", "PyTorch CUDA 이미지", image_ok, "기존 model-training image 변경"),
        check("05-env", "RANDOM_SIZE ConfigMap", env_ok, "model-training-env 연결"),
        check("05-repo", "AI26X-apps remote", repo_ok, "stopped Workbench PVC의 Git remote"),
        check("05-branch", "RHOAI3.3 branch", branch_ok, "stopped Workbench PVC의 branch"),
        check(
            "05-stopped",
            "검증 후 Workbench 중지",
            stopped_ok and file_ok,
            "kubeflow-resource-stopped, Pod 없음, train_model.ipynb 보존",
        ),
    ]


def grader_06(oc: Any, ns: str) -> list[Check]:
    requirements = Path.home() / "course" / "labs" / "workbench-custom" / "requirements.txt"
    requirement_ok = requirement_pinned(requirements, "seaborn", "0.13.2") and requirement_pinned(
        requirements, "python-json-logger", "2.0.7"
    )
    primary_image = "registry.lab.example.com:8443/developer/custom-workbench:1.0"
    alias_image = "registry.lab.example.com:8443/developer/custom-workbench-image:1.0"
    build_ok = requirement_ok and local_image_tags_same((primary_image, alias_image))
    image_stream = None
    for candidate in oc.list("imagestream.image.openshift.io", "redhat-ods-applications"):
        meta = candidate.get("metadata", {}) or {}
        if (
            (meta.get("labels", {}) or {}).get("opendatahub.io/notebook-image") == "true"
            and (meta.get("annotations", {}) or {}).get("opendatahub.io/notebook-image-name") == "custom-workbench"
        ):
            image_stream = candidate
            break
    source_ok = any(
        dig(tag, "from", "kind") == "DockerImage"
        and dig(tag, "from", "name")
        == alias_image
        for tag in (dig(image_stream, "spec", "tags", default=[]) or [])
    )
    metadata_ok = (
        image_annotation_is(
            image_stream,
            "opendatahub.io/notebook-image-desc",
            "The image provides the seaborn Python package.",
        )
        and image_software(image_stream, "Python", "3.12")
        and image_dependency(image_stream, "seaborn", "0.13.2")
        and image_dependency(image_stream, "python-json-logger", "2.0.7")
    )
    notebook = oc.get("notebook.kubeflow.org", "custom-wb", ns)
    notebook_ok = notebook_image_is(
        notebook,
        display_name="custom-workbench",
        image_tokens=("custom-workbench",),
    )
    runtime_ok = exec_ok(
        oc,
        ns,
        "custom-wb",
        [
            "python3",
            "-c",
            "import seaborn, pythonjsonlogger; from importlib.metadata import version; "
            "assert seaborn.__version__ == '0.13.2'; "
            "assert version('python-json-logger') == '2.0.7'",
        ],
    )
    return [
        check(
            "06-build",
            "Custom image dependencies와 dual tag",
            build_ok,
            "requirements pins and same image ID for custom-workbench/custom-workbench-image:1.0",
        ),
        check("06-import", "Custom image import", source_ok, "ImageStream source custom-workbench-image:1.0"),
        check("06-metadata", "Workbench image metadata", metadata_ok, "description/software/two package entries"),
        check("06-workbench", "custom-wb 생성", notebook_ok and pod_is_ready(oc, ns, "custom-wb"), "custom image Notebook Ready"),
        check("06-runtime", "두 package 실제 버전", runtime_ok, "seaborn 0.13.2, python-json-logger 2.0.7"),
    ]


TASK07_GIT_PROBE = r'''
import json
import pathlib
import subprocess

repo = pathlib.Path("/opt/app-root/src/AI26X-apps")
base_remote = "refs/remotes/origin/RHOAI3.3"
base_local = "refs/heads/RHOAI3.3"

def git(*args):
    return subprocess.run(
        ["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )

def ok(*args):
    return git(*args).returncode == 0

def output(*args):
    result = git(*args)
    return result.stdout.strip() if result.returncode == 0 else ""

is_repo = output("rev-parse", "--is-inside-work-tree") == "true"
remote = output("remote", "get-url", "origin") if is_repo else ""
current = output("branch", "--show-current") if is_repo else ""
base_refs = is_repo and ok("show-ref", "--verify", "--quiet", base_remote) and ok(
    "show-ref", "--verify", "--quiet", base_local
)

feature_branches = []
notebook_candidates = []
merged_candidates = []
if base_refs:
    refs = output("for-each-ref", "--format=%(refname)", "refs/heads").splitlines()
    for ref in refs:
        if ref == base_local or not ref.startswith("refs/heads/"):
            continue
        ahead_text = output("rev-list", "--count", f"{base_remote}..{ref}")
        try:
            ahead = int(ahead_text)
        except ValueError:
            ahead = 0
        if ahead < 1:
            continue
        branch = ref.removeprefix("refs/heads/")
        feature_branches.append(branch)
        diff = git(
            "diff",
            "--diff-filter=A",
            "--name-only",
            "-z",
            f"{base_remote}..{ref}",
            "--",
        )
        paths = []
        if diff.returncode == 0:
            paths = sorted(
                path
                for path in diff.stdout.split("\0")
                if path.lower().endswith(".ipynb")
                and ok("cat-file", "-e", f"{ref}:{path}")
                and not ok("cat-file", "-e", f"{base_remote}:{path}")
            )
        if not paths:
            continue
        candidate = {"branch": branch, "paths": paths}
        notebook_candidates.append(candidate)
        if ok("merge-base", "--is-ancestor", ref, base_local):
            merged_candidates.append(candidate)

print(json.dumps({
    "repository": base_refs
        and remote in {
            "https://github.com/RedHatTraining/AI26X-apps",
            "https://github.com/RedHatTraining/AI26X-apps.git",
        }
        and current == "RHOAI3.3",
    "feature_branches": sorted(feature_branches),
    "notebook_candidates": notebook_candidates,
    "merged_candidates": merged_candidates,
    "clean": is_repo and output("status", "--porcelain") == "",
}, sort_keys=True))
'''


def task07_git_evidence(oc: Any, namespace: str) -> dict[str, Any]:
    raw = exec_stdout(
        oc,
        namespace,
        "model-training",
        ["python3", "-c", TASK07_GIT_PROBE],
    )
    try:
        evidence = json.loads(raw.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError, TypeError):
        return {}
    return evidence if isinstance(evidence, dict) else {}


def grader_07(oc: Any, ns: str) -> list[Check]:
    evidence = task07_git_evidence(oc, ns)
    repository_ok = evidence.get("repository") is True
    feature_branches = {
        branch
        for branch in (evidence.get("feature_branches") or [])
        if isinstance(branch, str) and branch and branch != "RHOAI3.3"
    }
    notebook_candidates = [
        candidate
        for candidate in (evidence.get("notebook_candidates") or [])
        if isinstance(candidate, dict)
        and candidate.get("branch") in feature_branches
        and any(
            isinstance(path, str) and path.lower().endswith(".ipynb")
            for path in (candidate.get("paths") or [])
        )
    ]
    merged_candidates = [
        candidate
        for candidate in (evidence.get("merged_candidates") or [])
        if isinstance(candidate, dict)
        and any(
            candidate.get("branch") == notebook.get("branch")
            and candidate.get("paths") == notebook.get("paths")
            for notebook in notebook_candidates
        )
    ]
    branch_ok = bool(feature_branches)
    notebook_ok = bool(notebook_candidates)
    merge_ok = bool(merged_candidates)
    clean_ok = evidence.get("clean") is True
    return [
        check("07-repository", "AI26X-apps RHOAI3.3", repository_ok, "exact remote 및 current baseline branch"),
        check("07-branches", "feature branch commit", branch_ok, "이름이 자유인 local branch에 remote baseline 이후 commit 존재"),
        check("07-notebook", "새 Notebook 추적", notebook_ok, "feature branch에서 새 .ipynb 추가·commit"),
        check("07-merge", "feature branch 병합", merge_ok, "같은 feature branch가 local RHOAI3.3의 ancestor"),
        check("07-clean", "Workbench Ready·clean worktree", clean_ok and pod_is_ready(oc, ns, "model-training"), "Pod Ready 및 Git clean"),
    ]


def grader_08(oc: Any, ns: str) -> list[Check]:
    notebook = oc.get("notebook.kubeflow.org", "workbench-connections-wb", ns)
    secret = oc.get("secret", "my-s3-connection", ns)
    if secret is None:
        secret = oc.get("secret", "aws-connection-my-s3-connection", ns)
    connection_ok = s3_connection_matches(
        secret,
        access_key="minio",
        secret_key="minio123",
        endpoint="https://minio-api-minio.apps.lab.example.com",
        region="us-east-1",
        bucket="saved-models",
    ) and notebook_has_connection(notebook, ns, "my-s3-connection")
    repo = "/opt/app-root/src/AI26X-apps"
    local_ok = local_joblib_model_ok(oc, ns, "workbench-connections-wb", f"{repo}/carido-model.joblib")
    notebook_path = "workbench/connections/workbench-connections.ipynb"
    dataset_source = f"{repo}/workbench/connections/dataset.csv"
    dataset_downloaded = f"{repo}/workbench/connections/downloaded-dataset.csv"
    downloaded_model = f"{repo}/downloaded-carido-model.joblib"
    notebook_content = exec_stdout(
        oc,
        ns,
        "workbench-connections-wb",
        ["git", "-C", repo, "show", f"experiment2:{notebook_path}"],
    )
    notebook_ok = (
        notebook_executed_s3_transfer(
            notebook_content, "upload_file", "dataset.csv", "./dataset.csv"
        )
        and notebook_executed_s3_transfer(
            notebook_content,
            "download_file",
            "dataset.csv",
            "downloaded-dataset.csv",
        )
        and notebook_executed_joblib_save_cell(notebook_content)
        and notebook_executed_s3_transfer(
            notebook_content,
            "upload_file",
            "carido-model.joblib",
            f"{repo}/carido-model.joblib",
        )
        and notebook_executed_s3_transfer(
            notebook_content,
            "download_file",
            "carido-model.joblib",
            downloaded_model,
        )
    )
    branches_ok = git_check(
        oc,
        ns,
        "workbench-connections-wb",
        f"url=$(git -C {repo} remote get-url origin) && "
        "{ test \"$url\" = https://github.com/RedHatTraining/AI26X-apps.git || "
        "test \"$url\" = https://github.com/RedHatTraining/AI26X-apps; } && "
        f"test \"$(git -C {repo} branch --show-current)\" = RHOAI3.3 && "
        f"git -C {repo} show-ref --verify --quiet refs/heads/experiment2 && "
        f"git -C {repo} cat-file -e experiment2:{notebook_path} && "
        f"! git -C {repo} cat-file -e experiment2:carido-model.joblib 2>/dev/null && "
        f"! git -C {repo} cat-file -e experiment2:downloaded-carido-model.joblib 2>/dev/null && "
        f"! git -C {repo} diff --quiet origin/RHOAI3.3..experiment2 -- {notebook_path}",
    )
    merge_ok = git_check(
        oc,
        ns,
        "workbench-connections-wb",
        f"git -C {repo} show-ref --verify --quiet refs/remotes/origin/RHOAI3.3 && "
        f"git -C {repo} merge-base --is-ancestor experiment2 RHOAI3.3 && "
        f"test \"$(git -C {repo} rev-list --count origin/RHOAI3.3..experiment2)\" -ge 1 && "
        f"test -z \"$(git -C {repo} status --porcelain)\"",
    )
    dataset_object_ok = s3_object_matches_local(
        oc,
        ns,
        "workbench-connections-wb",
        dataset_source,
        "dataset.csv",
        dataset_downloaded,
    )
    model_object_ok = s3_object_matches_local(
        oc,
        ns,
        "workbench-connections-wb",
        f"{repo}/carido-model.joblib",
        "carido-model.joblib",
        downloaded_model,
    )
    object_ok = dataset_object_ok and model_object_ok
    return [
        check("08-connection", "S3 connection 연결", connection_ok, "my-s3-connection/saved-models와 Notebook 참조"),
        check("08-local", "학습 Notebook과 로컬 model artifact", local_ok and notebook_ok, "실행된 save cell과 AI26X-apps/carido-model.joblib"),
        check("08-branch", "experiment2 branch", branches_ok, "workbench-connections.ipynb commit 존재"),
        check("08-merge", "RHOAI3.3 병합", merge_ok, "experiment2 ancestor"),
        check(
            "08-object",
            "S3 dataset/model artifact round trip",
            object_ok,
            "remote/downloaded dataset.csv and carido-model.joblib exactly match local source bytes",
        ),
    ]


def grader_09(oc: Any, ns: str) -> list[Check]:
    target_ns = "tiger"
    project = oc.get("namespace", target_ns)
    secret = oc.get("secret", "rhoaiserving-using", target_ns)
    if secret is None:
        secret = oc.get("secret", "aws-connection-rhoaiserving-using", target_ns)
    connection_ok = project is not None and s3_connection_matches(
        secret,
        access_key="minio",
        secret_key="minio123",
        endpoint="https://minio-api-minio.apps.lab.example.com",
        region="us-east-1",
        bucket="models-bucket",
    )

    service = oc.get("inferenceservice.serving.kserve.io", "diabetes", target_ns)
    model = dig(service, "spec", "predictor", "model", default={}) or {}
    runtime_name = str(model.get("runtime", ""))
    model_format = model.get("modelFormat", {}) or {}
    storage = model.get("storage", {}) or {}
    storage_key = str(storage.get("key", ""))
    storage_path = str(storage.get("path", "")).strip("/")
    storage_uri = str(model.get("storageUri", "")).rstrip("/")
    storage_ok = (
        storage_key in {"rhoaiserving-using", "aws-connection-rhoaiserving-using"}
        and storage_path == "models/diabetes"
    ) or storage_uri == "s3://models-bucket/models/diabetes"
    spec_ok = (
        str(annotations(service).get("serving.kserve.io/deploymentMode", "")).lower()
        == "rawdeployment"
        and str(model_format.get("name", "")).lower() == "onnx"
        and str(model_format.get("version", "")) == "1"
        and storage_ok
        and serving_runtime_is_openvino_onnx(oc, target_ns, runtime_name)
    )
    ready_ok = ready(service)
    routes = [
        route
        for route in oc.list("route.route.openshift.io", target_ns)
        if resource_name(route) == "diabetes" or resource_name(route).startswith("diabetes-")
    ]
    route = next((item for item in routes if bool(dig(item, "spec", "host"))), None)
    auth_disabled = annotations(service).get("security.opendatahub.io/enable-auth") == "false"
    route_ok = route is not None and auth_disabled
    inference_ok = bool(
        route
        and unauthenticated_v2_inference_ok(str(dig(route, "spec", "host", default="")), "diabetes")
    )
    return [
        check("09-project", "tiger 프로젝트와 S3 connection", connection_ok, "rhoaiserving-using exact credentials/bucket"),
        check("09-spec", "diabetes InferenceService", spec_ok, "OpenVINO runtime, RawDeployment, onnx-1, connection/path"),
        check("09-ready", "InferenceService Started", ready_ok, "diabetes Ready=True"),
        check("09-route", "외부 Route·인증 비활성", route_ok, "Route host 및 enable-auth=false"),
        check("09-inference", "무인증 KServe V2 추론", inference_ok, "/v2/models/diabetes/infer HTTP 200"),
    ]


def grader_10(oc: Any, ns: str) -> list[Check]:
    dspas = oc.list("datasciencepipelinesapplication.datasciencepipelinesapplications.opendatahub.io", ns)
    dspa_ok = any(dspa_ready(item) for item in dspas)
    compiled_content = read_text_if_file("/tmp/simple_rhoai_pipeline.yaml")
    compiled_ok = compiled_kfp_ir_matches(compiled_content, "tas1-devops-wala", "2.15.2")
    schedules = oc.list("scheduledworkflow.kubeflow.org", ns)
    schedule = next((item for item in schedules if workflow_named(item, "tas1-devops-wala-s1")), None)
    schedule_exists = bool(schedule and schedule_references_pipeline(schedule, "tas1-devops-wala"))
    schedule_ok = bool(schedule and schedule_is_enabled_five_minutes(schedule))
    all_workflows = workflows(oc, ns)
    run_ok = bool(schedule and any(workflow_links_to_schedule(item, schedule) for item in all_workflows))
    return [
        check("10-dspa", "Pipeline Server Ready", dspa_ok, "DSPA Ready=True"),
        check("10-compile", "KFP 2.15.2 pipeline compile", compiled_ok, "simple_rhoai_pipeline.yaml/tas1-devops-wala"),
        check("10-import", "Pipeline schedule 연결", schedule_exists, "tas1-devops-wala-s1 존재"),
        check("10-schedule", "활성 5분 schedule", schedule_ok, "Periodic intervalSecond=300"),
        check("10-run", "Scheduled run 성공", run_ok, "schedule-linked Workflow Succeeded"),
    ]


def grader_11(oc: Any, ns: str) -> list[Check]:
    dspas = oc.list("datasciencepipelinesapplication.datasciencepipelinesapplications.opendatahub.io", ns)
    connection = oc.get("secret", "my-s3-connection", ns)
    connection_ok = s3_connection_matches(
        connection,
        access_key="minio",
        secret_key="minio123",
        endpoint="https://minio-api-minio.apps.lab.example.com",
        region="us-east-1",
        bucket="saved-models",
    )
    dspa = next(
        (
            item
            for item in dspas
            if dspa_ready(item)
            and dig(item, "spec", "objectStorage", "externalStorage", "bucket") == "saved-models"
            and dig(
                item,
                "spec",
                "objectStorage",
                "externalStorage",
                "s3CredentialsSecret",
                "secretName",
            )
            == "my-s3-connection"
        ),
        None,
    )
    dspa_ok = dspa is not None and connection_ok
    pods_ok = pipeline_server_pods_ready(oc, ns)

    compiled_content = read_text_if_file("/tmp/ai267-task11/carido-training-pipeline.yaml")
    stages = ["generate-data", "preprocess-data", "train-model", "save-model"]
    compiled_ok = compiled_kfp_ir_matches(
        compiled_content,
        "carido-training-pipeline",
        "2.15.2",
    ) and compiled_pipeline_has_ordered_chain(compiled_content, stages)

    run = next(
        (
            item
            for item in workflows(oc, ns)
            if workflow_named(item, "carido-training-r1") and phase(item).lower() == "succeeded"
        ),
        None,
    )
    run_ok = bool(run and workflow_stages_succeeded(run, stages))
    artifact_ok = s3_fixture_object_exists("saved-models", "carido-model.joblib")
    return [
        check("11-dspa", "Pipeline Server와 object storage", dspa_ok, "Ready DSPA uses my-s3-connection/saved-models"),
        check("11-pods", "Pipeline 구성 요소", pods_ok, "API/persistence/scheduler Pods Ready"),
        check("11-compile", "4단계 KFP 2.15.2 pipeline", compiled_ok, "carido-training-pipeline.yaml"),
        check("11-run", "carido 4단계 run", run_ok, "carido-training-r1 and all stages Succeeded"),
        check(
            "11-artifact",
            "S3 root model object",
            artifact_ok,
            "saved-models/carido-model.joblib GET body is non-empty",
        ),
    ]


def grader_12(oc: Any, ns: str) -> list[Check]:
    dspas = oc.list("datasciencepipelinesapplication.datasciencepipelinesapplications.opendatahub.io", ns)
    dspa_ok = any(dspa_ready(item) for item in dspas)
    notebook_name = "pipelines-elyra-wb"
    notebook = oc.get("notebook.kubeflow.org", notebook_name, ns)
    workbench_ok = (
        notebook_image_is(
            notebook,
            display_name="Jupyter | Data Science | CPU | Python 3.12",
            image_tokens=("generic-data-science",),
        )
        and notebook_has_bound_storage(oc, ns, notebook, {"10Gi", "10240Mi"})
        and notebook_has_connection(notebook, ns, "s3-minio")
        and pod_is_ready(oc, ns, notebook_name)
    )
    repository_ok = git_check(
        oc,
        ns,
        notebook_name,
        "url=$(git -C /opt/app-root/src/AI26X-apps remote get-url origin) && "
        "{ test \"$url\" = https://github.com/RedHatTraining/AI26X-apps.git || "
        "test \"$url\" = https://github.com/RedHatTraining/AI26X-apps; } && "
        "test \"$(git -C /opt/app-root/src/AI26X-apps branch --show-current)\" = RHOAI3.3 && "
        "test -f /opt/app-root/src/AI26X-apps/dspa/elyra/issues_prediction.pipeline",
    )
    pipeline_content = exec_stdout(
        oc,
        ns,
        notebook_name,
        ["cat", "/opt/app-root/src/AI26X-apps/dspa/elyra/issues_prediction.pipeline"],
    )
    nodes_ok, outputs_ok = elyra_pipeline_checks(pipeline_content)
    pipeline_ok = (
        nodes_ok
        and outputs_ok
        and elyra_pipeline_settings_ok(pipeline_content)
        and elyra_runtime_image_metadata_ok(oc, ns, notebook_name)
    )
    run_ok = any(
        workflow_named(item, "issues_prediction") and phase(item).lower() == "succeeded"
        for item in workflows(oc, ns)
    )
    s3_ok = s3_prefix_has(
        oc,
        ns,
        notebook_name,
        ["data.csv", "clean-data.csv", "forecast-data.csv"],
    )
    return [
        check(
            "12-workbench",
            "10 GiB Data Science Workbench",
            workbench_ok,
            "pipelines-elyra-wb Ready, s3-minio attached",
        ),
        check("12-repository", "AI26X-apps RHOAI3.3", repository_ok, "exact remote/branch/path"),
        check(
            "12-pipeline",
            "Elyra runtime·Secret·3-node graph",
            pipeline_ok,
            "custom image, exact four mappings, ordered nodes and outputs",
        ),
        check("12-run", "issues_prediction run", dspa_ok and run_ok, "DSPA Ready and Workflow Succeeded"),
        check("12-s3", "S3 결과 파일", s3_ok, "timestamp folder의 세 output"),
    ]


GRADERS: dict[str, Callable[[Any, str], list[Check]]] = {
    "01": grader_01,
    "02": grader_02,
    "03": grader_03,
    "04": grader_04,
    "05": grader_05,
    "06": grader_06,
    "07": grader_07,
    "08": grader_08,
    "09": grader_09,
    "10": grader_10,
    "11": grader_11,
    "12": grader_12,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=sorted(TASKS))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    task = TASKS[args.task]
    results = GRADERS[args.task](Oc(), task.namespace)
    maximum = sum(item.points for item in results)
    score = sum(item.points for item in results if item.passed)
    passed = score == maximum == task.points

    if args.json:
        print(
            json.dumps(
                {
                    "task": task.task_id,
                    "title": task.title,
                    "namespace": task.namespace,
                    "score": score,
                    "maximum": maximum,
                    "passed": passed,
                    "checks": [asdict(item) for item in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"Task {task.task_id} · {task.title}")
        print(f"Project: {task.namespace}\n")
        for item in results:
            marker = "PASS" if item.passed else "FAIL"
            print(f"[{marker}] {item.points:>3}  {item.title}")
            print(f"       {item.detail}")
        print(f"\nScore: {score}/{maximum}")
        print("Result: PASS" if passed else "Result: NOT YET")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
