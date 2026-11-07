#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-12"
readonly NAMESPACE=dspa-elyra
readonly COMPAT_SECRET=aws-connection-s3-minio

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/compat-secret.created" 2>/dev/null || true)" == true ]]; then
  if oc get namespace "${NAMESPACE}" >/dev/null 2>&1 \
    && oc get secret "${COMPAT_SECRET}" -n "${NAMESPACE}" >/dev/null 2>&1; then
    owner=$(oc get secret "${COMPAT_SECRET}" -n "${NAMESPACE}" \
      -o jsonpath='{.metadata.labels.ai267\.practice/created-by}')
    if [[ "${owner}" != task-12 ]]; then
      printf '%s Secret의 ownership label이 달라 삭제하지 않았습니다.\n' "${COMPAT_SECRET}" >&2
      exit 1
    fi
    oc delete secret "${COMPAT_SECRET}" -n "${NAMESPACE}" \
      --ignore-not-found=true >/dev/null
  fi
fi

rm -f -- "${TASK_STATE_ROOT}/compat-secret.created"
rmdir "${TASK_STATE_ROOT}" 2>/dev/null || true
