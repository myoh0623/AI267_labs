#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PRACTICE_ROOT=$(cd -- "${TASK_DIR}/../.." && pwd)
readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-04"
readonly S3_HELPER="${PRACTICE_ROOT}/tasks/common/s3_fixture.py"
readonly PROJECT=projects-data
readonly BUCKET=projects-data-bucket

# S3 또는 프로젝트를 변경하기 전에 task-created namespace인지 확인한다.
if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/project.created" 2>/dev/null || true)" == true ]] \
  && oc get namespace "${PROJECT}" >/dev/null 2>&1; then
  project_owner=$(oc get namespace "${PROJECT}" \
    -o jsonpath='{.metadata.labels.ai267\.practice/created-by}')
  if [[ "${project_owner}" != task-04 ]]; then
    printf 'Task 04 cleanup 거부: %s 프로젝트 ownership이 다릅니다.\n' \
      "${PROJECT}" >&2
    exit 1
  fi
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/bucket.absent-at-start" 2>/dev/null || true)" == true ]]; then
  python3 "${S3_HELPER}" purge-bucket "${BUCKET}"
  python3 "${S3_HELPER}" delete-bucket "${BUCKET}"
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/project.created" 2>/dev/null || true)" == true ]]; then
  oc delete project "${PROJECT}" --ignore-not-found=true
fi

rm -f -- "${TASK_STATE_ROOT}/bucket.absent-at-start" \
  "${TASK_STATE_ROOT}/project.created"
rmdir "${TASK_STATE_ROOT}" 2>/dev/null || true
