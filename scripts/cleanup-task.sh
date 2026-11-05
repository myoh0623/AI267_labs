#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$1
shift
namespace=$(lab_task_namespace "${task}")
auto_approve=false
[[ "${1:-}" == --yes ]] && auto_approve=true

lab_require_login
if ! oc get namespace "${namespace}" >/dev/null 2>&1; then
  lab_log "Namespace ${namespace} does not exist. Nothing to remove."
  exit 0
fi

lab_verify_managed_namespace "${task}" "${namespace}" \
  || lab_die "Namespace ${namespace} is not labeled as the managed namespace for task ${task}. Refusing to delete it."

if [[ "${auto_approve}" == true ]]; then
  confirmation=${namespace}
else
  printf 'This deletes namespace %s and every resource in it.\n' "${namespace}"
  read -r -p "Type ${namespace} to continue: " confirmation
fi

[[ "${confirmation}" == "${namespace}" ]] || lab_die 'Cleanup cancelled.'
oc delete namespace "${namespace}" --wait=true --timeout=300s

