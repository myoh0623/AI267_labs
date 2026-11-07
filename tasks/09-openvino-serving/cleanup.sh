#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PRACTICE_ROOT=$(cd -- "${TASK_DIR}/../.." && pwd)
readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-09"
readonly S3_HELPER="${PRACTICE_ROOT}/tasks/common/s3_fixture.py"
readonly BUCKET=models-bucket
readonly OBJECT_KEY=models/diabetes/1/model.onnx
readonly OWNER_KEY=.ai267-practice-task-09-owner
readonly OWNER_TOKEN="${TASK_STATE_ROOT}/bucket-owner.token"

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/bucket.present" 2>/dev/null || true)" == false ]]; then
  [[ -s "${OWNER_TOKEN}" ]] || {
    printf 'Task 09 cleanup 거부: S3 ownership token이 없습니다.\n' >&2
    exit 1
  }
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/bucket.present" 2>/dev/null || true)" == false ]]; then
  python3 "${S3_HELPER}" delete-owned-bucket \
    "${BUCKET}" "${OWNER_KEY}" "${OWNER_TOKEN}"
elif [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/object.present" 2>/dev/null || true)" == true ]] \
  && [[ -f "${TASK_STATE_ROOT}/original-model.onnx" ]]; then
  python3 "${S3_HELPER}" upload "${BUCKET}" "${OBJECT_KEY}" \
    "${TASK_STATE_ROOT}/original-model.onnx"
elif [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/object.present" 2>/dev/null || true)" == false ]]; then
  python3 "${S3_HELPER}" delete-object "${BUCKET}" "${OBJECT_KEY}"
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/tiger.present" 2>/dev/null || true)" == false ]]; then
  oc delete project tiger --ignore-not-found=true
fi

rm -f -- "${TASK_STATE_ROOT}/tiger.present" \
  "${TASK_STATE_ROOT}/bucket.present" \
  "${TASK_STATE_ROOT}/object.present" \
  "${TASK_STATE_ROOT}/original-model.onnx" \
  "${TASK_STATE_ROOT}/diabetes-model.onnx" \
  "${OWNER_TOKEN}"
rmdir "${TASK_STATE_ROOT}" 2>/dev/null || true
