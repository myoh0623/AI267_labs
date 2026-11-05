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

if [[ "${task}" == 01 ]]; then
  auth_backup=$(oc get configmap exam-provided-auth-backup -n "${namespace}" \
    -o jsonpath='{.data.auth\.json}' 2>/dev/null || true)
  if [[ -n "${auth_backup}" && "${auth_backup}" != '{}' ]]; then
    printf '%s\n' "${auth_backup}" | oc apply -f - >/dev/null
    lab_log "Task 01 시작 전 OpenShift AI Auth 설정을 복원했습니다."
  fi
  unset auth_backup

  for group_name in devops-wala rhoai-exam-admins; do
    group_task=$(oc get group "${group_name}" \
      -o jsonpath='{.metadata.labels.ex267\.practice/task}' 2>/dev/null || true)
    if [[ "${group_task}" == 01 ]]; then
      oc delete group "${group_name}" --ignore-not-found >/dev/null
    fi
  done
fi

if [[ "${task}" == 02 ]]; then
  culler_existed=$(oc get configmap exam-provided-culler-backup -n "${namespace}" \
    -o jsonpath='{.data.existed}' 2>/dev/null || true)
  culler_backup=$(oc get configmap exam-provided-culler-backup -n "${namespace}" \
    -o jsonpath='{.data.culler\.json}' 2>/dev/null || true)
  if [[ "${culler_existed}" == true && -n "${culler_backup}" && "${culler_backup}" != '{}' ]]; then
    printf '%s\n' "${culler_backup}" | oc apply -f - >/dev/null
    lab_log "Task 02 시작 전 notebook culler 설정을 복원했습니다."
  elif [[ "${culler_existed}" == false ]]; then
    culler_task=$(oc get configmap notebook-controller-culler-config -n redhat-ods-applications \
      -o jsonpath='{.metadata.labels.ex267\.practice/task}' 2>/dev/null || true)
    if [[ "${culler_task}" == 02 ]]; then
      oc delete configmap notebook-controller-culler-config -n redhat-ods-applications \
        --ignore-not-found >/dev/null
      lab_log "Task 02에서 생성한 notebook culler 설정을 제거했습니다."
    else
      lab_log "Task 02 소유 라벨이 없는 cluster-wide culler 설정은 삭제하지 않았습니다."
    fi
    unset culler_task
  fi
  unset culler_existed culler_backup
fi

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

