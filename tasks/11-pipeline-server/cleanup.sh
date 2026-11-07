#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PRACTICE_ROOT=$(cd -- "${TASK_DIR}/../.." && pwd)
readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-11"
readonly S3_HELPER="${PRACTICE_ROOT}/tasks/common/s3_fixture.py"
readonly WORK_DIR=/tmp/ai267-task11
readonly BUCKET=saved-models
readonly OWNER_KEY=.ai267-practice-task-11-owner
readonly OWNER_TOKEN="${TASK_STATE_ROOT}/bucket-owner.token"

# 어떤 리소스도 변경하기 전에 이름이 재사용되지 않았는지 검증한다.
if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/bucket.created" 2>/dev/null || true)" == true ]] \
  && [[ ! -s "${OWNER_TOKEN}" ]]; then
  printf 'Task 11 cleanup 거부: S3 ownership token이 없습니다.\n' >&2
  exit 1
fi
if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/secret.created" 2>/dev/null || true)" == true ]] \
  && oc get secret -n dspa-intro my-s3-connection >/dev/null 2>&1; then
  secret_owner=$(oc get secret -n dspa-intro my-s3-connection \
    -o jsonpath='{.metadata.labels.ai267\.practice/created-by}')
  if [[ "${secret_owner}" != task-11 ]]; then
    printf 'Task 11 cleanup 거부: dspa-intro/my-s3-connection ownership이 다릅니다.\n' >&2
    exit 1
  fi
fi
if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/workdir.created" 2>/dev/null || true)" == true ]] \
  && [[ -e "${WORK_DIR}" || -L "${WORK_DIR}" ]]; then
  if [[ ! -d "${WORK_DIR}" || -L "${WORK_DIR}" \
    || "$(sed -n '1p' "${WORK_DIR}/.ai267-task-owned" 2>/dev/null || true)" != task-11 ]]; then
    printf 'Task 11 cleanup 거부: %s ownership marker가 없습니다.\n' "${WORK_DIR}" >&2
    exit 1
  fi
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/bucket.created" 2>/dev/null || true)" == true ]]; then
  python3 "${S3_HELPER}" delete-owned-bucket \
    "${BUCKET}" "${OWNER_KEY}" "${OWNER_TOKEN}"
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/secret.created" 2>/dev/null || true)" == true ]]; then
  oc delete secret -n dspa-intro my-s3-connection --ignore-not-found=true
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/workdir.created" 2>/dev/null || true)" == true ]]; then
  rm -rf -- "${WORK_DIR}"
fi

rm -f -- "${TASK_STATE_ROOT}/bucket.created" \
  "${TASK_STATE_ROOT}/secret.created" \
  "${TASK_STATE_ROOT}/workdir.created" \
  "${OWNER_TOKEN}"
rmdir "${TASK_STATE_ROOT}" 2>/dev/null || true
