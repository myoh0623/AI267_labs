#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-02"
readonly BACKUP_COMPLETE="${TASK_STATE_ROOT}/backup-complete"

mkdir -p "${TASK_STATE_ROOT}"
chmod 700 "${TASK_STATE_ROOT}"

if [[ -e "${BACKUP_COMPLETE}" ]]; then
  printf 'Task 02의 완료된 백업이 이미 있습니다. 먼저 ai267 finish 02를 실행하세요.\n' >&2
  exit 1
fi

# No cluster mutation happens before all three snapshots have been captured,
# parsed, and atomically installed. Cleanup refuses to run without the marker.
rm -f -- "${TASK_STATE_ROOT}"/*.tmp \
  "${TASK_STATE_ROOT}/auth-spec.json" \
  "${TASK_STATE_ROOT}/groups.json" \
  "${TASK_STATE_ROOT}/clusterrolebindings.json" \
  "${TASK_STATE_ROOT}/created-users.txt"

auth_tmp="${TASK_STATE_ROOT}/auth-spec.json.tmp"
groups_tmp="${TASK_STATE_ROOT}/groups.json.tmp"
bindings_tmp="${TASK_STATE_ROOT}/clusterrolebindings.json.tmp"

oc get auth.services.platform.opendatahub.io auth -o json \
  | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["spec"], separators=(",", ":")))' \
  > "${auth_tmp}"
oc get group.user.openshift.io -o json > "${groups_tmp}"
oc get clusterrolebinding.rbac.authorization.k8s.io -o json > "${bindings_tmp}"

python3 - "${auth_tmp}" "${groups_tmp}" "${bindings_tmp}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    auth_spec = json.load(stream)
if not isinstance(auth_spec, dict):
    raise SystemExit("Auth spec backup is not a JSON object")

for path, kind in ((sys.argv[2], "GroupList"), (sys.argv[3], "ClusterRoleBindingList")):
    with open(path, encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise SystemExit(f"{kind} backup is not a valid Kubernetes list")
PY

mv -- "${auth_tmp}" "${TASK_STATE_ROOT}/auth-spec.json"
mv -- "${groups_tmp}" "${TASK_STATE_ROOT}/groups.json"
mv -- "${bindings_tmp}" "${TASK_STATE_ROOT}/clusterrolebindings.json"
: > "${TASK_STATE_ROOT}/created-users.txt"
chmod 600 "${TASK_STATE_ROOT}/auth-spec.json" \
  "${TASK_STATE_ROOT}/groups.json" \
  "${TASK_STATE_ROOT}/clusterrolebindings.json" \
  "${TASK_STATE_ROOT}/created-users.txt"
printf 'complete\n' > "${TASK_STATE_ROOT}/backup-complete.tmp"
mv -- "${TASK_STATE_ROOT}/backup-complete.tmp" "${BACKUP_COMPLETE}"
chmod 600 "${BACKUP_COMPLETE}"

for practice_user in developer suraj rajan punit raja andrew; do
  if ! oc get user.user.openshift.io "${practice_user}" >/dev/null 2>&1; then
    oc create user "${practice_user}"
    printf '%s\n' "${practice_user}" >> "${TASK_STATE_ROOT}/created-users.txt"
  fi
done
