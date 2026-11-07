#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-01"
readonly PROJECT=my-lab-pro
readonly PROFILE_NAMESPACE=redhat-ods-applications
readonly PROFILE=task01-2cpu-8gi

if [[ -f "${TASK_STATE_ROOT}/created-users.txt" ]]; then
  while IFS= read -r practice_user; do
    case "${practice_user}" in
      suraj|rajan|punit|'') ;;
      *)
        printf 'Task 01 cleanup 거부: 알 수 없는 생성 사용자 %s\n' "${practice_user}" >&2
        exit 1
        ;;
    esac
  done < "${TASK_STATE_ROOT}/created-users.txt"
fi

# 어떤 리소스도 지우기 전에 cluster-scoped profile의 ownership을 검증한다.
if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/profile.created" 2>/dev/null || true)" == true ]] \
  && oc get hardwareprofile.infrastructure.opendatahub.io "${PROFILE}" \
    -n "${PROFILE_NAMESPACE}" >/dev/null 2>&1; then
  profile_owner=$(oc get hardwareprofile.infrastructure.opendatahub.io "${PROFILE}" \
    -n "${PROFILE_NAMESPACE}" \
    -o jsonpath='{.metadata.labels.ai267\.practice/created-by}')
  if [[ "${profile_owner}" != task-01 ]]; then
    printf 'Task 01 cleanup 거부: %s/%s HardwareProfile ownership이 다릅니다.\n' \
      "${PROFILE_NAMESPACE}" "${PROFILE}" >&2
    exit 1
  fi
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/project.absent-at-start" 2>/dev/null || true)" == true ]]; then
  oc delete project "${PROJECT}" --ignore-not-found=true
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/profile.created" 2>/dev/null || true)" == true ]]; then
  oc delete hardwareprofile.infrastructure.opendatahub.io "${PROFILE}" \
    -n "${PROFILE_NAMESPACE}" --ignore-not-found=true
fi

if [[ -f "${TASK_STATE_ROOT}/created-users.txt" ]]; then
  while IFS= read -r practice_user; do
    [[ -n "${practice_user}" ]] || continue
    oc delete user.user.openshift.io "${practice_user}" --ignore-not-found=true
  done < "${TASK_STATE_ROOT}/created-users.txt"
fi

rm -f -- "${TASK_STATE_ROOT}/project.absent-at-start" \
  "${TASK_STATE_ROOT}/profile.created" \
  "${TASK_STATE_ROOT}/created-users.txt"
rmdir "${TASK_STATE_ROOT}" 2>/dev/null || true
