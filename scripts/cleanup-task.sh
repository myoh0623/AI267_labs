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

if [[ "${task}" == 08 ]] && lab_api_available trustyai.opendatahub.io lmevaljobs; then
  # LMEvalJobs can keep their finalizer and Pending worker Pods after namespace
  # deletion starts. This namespace is verified as practice-lab managed, so
  # terminate those evaluation resources before removing the namespace.
  while IFS= read -r job_name; do
    [[ -n "${job_name}" ]] || continue
    oc patch "${job_name}" -n "${namespace}" --type=merge \
      -p '{"metadata":{"finalizers":[]}}' >/dev/null 2>&1 || true
  done < <(oc get lmevaljobs -n "${namespace}" -o name 2>/dev/null || true)
  oc delete lmevaljobs -n "${namespace}" --all --wait=false --ignore-not-found >/dev/null 2>&1 || true
  oc delete pods -n "${namespace}" --all --wait=false --ignore-not-found >/dev/null 2>&1 || true
fi

oc delete namespace "${namespace}" --wait=true --timeout=300s

