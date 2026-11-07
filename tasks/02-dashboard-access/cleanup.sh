#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-02"
readonly BACKUP_COMPLETE="${TASK_STATE_ROOT}/backup-complete"

if [[ "$(sed -n '1p' "${BACKUP_COMPLETE}" 2>/dev/null || true)" != complete ]]; then
  printf 'Task 02 cleanup 거부: 완전한 백업 표식이 없습니다. 클러스터를 변경하지 않았습니다.\n' >&2
  exit 1
fi

if ! python3 - \
  "${TASK_STATE_ROOT}/auth-spec.json" \
  "${TASK_STATE_ROOT}/groups.json" \
  "${TASK_STATE_ROOT}/clusterrolebindings.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    auth_spec = json.load(stream)
if not isinstance(auth_spec, dict):
    raise SystemExit("invalid Auth spec backup")

for path in sys.argv[2:]:
    with open(path, encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise SystemExit(f"invalid Kubernetes list backup: {path}")
PY
then
  printf 'Task 02 cleanup 거부: 백업 JSON이 없거나 손상되었습니다. 클러스터를 변경하지 않았습니다.\n' >&2
  exit 1
fi

if [[ -f "${TASK_STATE_ROOT}/created-users.txt" ]]; then
  while IFS= read -r practice_user; do
    case "${practice_user}" in
      developer|suraj|rajan|punit|raja|andrew|'') ;;
      *)
        printf 'Task 02 cleanup 거부: 알 수 없는 생성 사용자 %s\n' "${practice_user}" >&2
        exit 1
        ;;
    esac
  done < "${TASK_STATE_ROOT}/created-users.txt"
fi

auth_patch=$(python3 - "${TASK_STATE_ROOT}/auth-spec.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    print(json.dumps([{"op": "replace", "path": "/spec", "value": json.load(stream)}]))
PY
)
oc patch auth.services.platform.opendatahub.io auth --type=json -p "${auth_patch}"

python3 - "${TASK_STATE_ROOT}/groups.json" "${TASK_STATE_ROOT}/clusterrolebindings.json" <<'PY'
import json
import subprocess
import sys

target_users = {"developer", "suraj", "rajan", "punit", "raja", "andrew"}
target_groups = {"devops-wala", "ai267-admins"}


def oc_json(*args):
    return json.loads(subprocess.check_output(["oc", *args], text=True))


def oc_run(*args, input_text=None):
    subprocess.run(["oc", *args], input=input_text, text=True, check=True)


with open(sys.argv[1], encoding="utf-8") as stream:
    original_group_list = json.load(stream).get("items", [])
with open(sys.argv[2], encoding="utf-8") as stream:
    original_binding_list = json.load(stream).get("items", [])

original_groups = {item["metadata"]["name"]: item for item in original_group_list}
current_groups = {
    item["metadata"]["name"]: item
    for item in oc_json("get", "group.user.openshift.io", "-o", "json").get("items", [])
}
affected_groups = set(target_groups)
affected_groups.update(
    name
    for name, item in original_groups.items()
    if set(item.get("users", [])) & target_users
)
affected_groups.update(
    name
    for name, item in current_groups.items()
    if set(item.get("users", [])) & target_users
)
for name in sorted(affected_groups):
    original = original_groups.get(name)
    current = current_groups.get(name)
    if original is not None:
        users = original.get("users", [])
        if current is None:
            metadata = original.get("metadata", {})
            manifest = {
                "apiVersion": "user.openshift.io/v1",
                "kind": "Group",
                "metadata": {
                    "name": name,
                    "labels": metadata.get("labels", {}),
                    "annotations": metadata.get("annotations", {}),
                },
                "users": users,
            }
            oc_run("apply", "-f", "-", input_text=json.dumps(manifest))
        else:
            oc_run(
                "patch",
                "group.user.openshift.io",
                name,
                "--type=merge",
                "-p",
                json.dumps({"users": users}, separators=(",", ":")),
            )
    elif current is not None and name in target_groups:
        oc_run("delete", "group.user.openshift.io", name, "--ignore-not-found=true")
    elif current is not None:
        users = [user for user in current.get("users", []) if user not in target_users]
        if users:
            oc_run(
                "patch",
                "group.user.openshift.io",
                name,
                "--type=merge",
                "-p",
                json.dumps({"users": users}, separators=(",", ":")),
            )
        else:
            oc_run("delete", "group.user.openshift.io", name, "--ignore-not-found=true")


def relevant_subject(subject):
    return (
        subject.get("kind") == "User" and subject.get("name") in target_users
    ) or (
        subject.get("kind") == "Group" and subject.get("name") in affected_groups
    )


original_bindings = {item["metadata"]["name"]: item for item in original_binding_list}
current_binding_items = oc_json(
    "get", "clusterrolebinding.rbac.authorization.k8s.io", "-o", "json"
).get("items", [])
current_bindings = {item["metadata"]["name"]: item for item in current_binding_items}
affected_bindings = {
    name
    for name, item in original_bindings.items()
    if any(relevant_subject(subject) for subject in item.get("subjects", []))
}
affected_bindings.update(
    name
    for name, item in current_bindings.items()
    if any(relevant_subject(subject) for subject in item.get("subjects", []))
)
for name in sorted(affected_bindings):
    original = original_bindings.get(name)
    current = current_bindings.get(name)
    if original is not None:
        subjects = original.get("subjects", [])
        if current is None:
            metadata = original.get("metadata", {})
            manifest = {
                "apiVersion": original.get("apiVersion", "rbac.authorization.k8s.io/v1"),
                "kind": "ClusterRoleBinding",
                "metadata": {
                    "name": name,
                    "labels": metadata.get("labels", {}),
                    "annotations": metadata.get("annotations", {}),
                },
                "roleRef": original["roleRef"],
                "subjects": subjects,
            }
            oc_run("apply", "-f", "-", input_text=json.dumps(manifest))
        else:
            oc_run(
                "patch",
                "clusterrolebinding.rbac.authorization.k8s.io",
                name,
                "--type=merge",
                "-p",
                json.dumps({"subjects": subjects}, separators=(",", ":")),
            )
    elif current is not None:
        subjects = [
            subject for subject in current.get("subjects", []) if not relevant_subject(subject)
        ]
        if subjects:
            oc_run(
                "patch",
                "clusterrolebinding.rbac.authorization.k8s.io",
                name,
                "--type=merge",
                "-p",
                json.dumps({"subjects": subjects}, separators=(",", ":")),
            )
        else:
            oc_run(
                "delete",
                "clusterrolebinding.rbac.authorization.k8s.io",
                name,
                "--ignore-not-found=true",
            )
PY

if [[ -f "${TASK_STATE_ROOT}/created-users.txt" ]]; then
  while IFS= read -r practice_user; do
    [[ -n "${practice_user}" ]] || continue
    oc delete user.user.openshift.io "${practice_user}" --ignore-not-found=true
  done < "${TASK_STATE_ROOT}/created-users.txt"
fi

rm -f -- "${TASK_STATE_ROOT}/auth-spec.json" \
  "${TASK_STATE_ROOT}/groups.json" \
  "${TASK_STATE_ROOT}/groups.json.tmp" \
  "${TASK_STATE_ROOT}/clusterrolebindings.json" \
  "${TASK_STATE_ROOT}/clusterrolebindings.json.tmp" \
  "${TASK_STATE_ROOT}/created-users.txt" \
  "${BACKUP_COMPLETE}"
rmdir "${TASK_STATE_ROOT}" 2>/dev/null || true
