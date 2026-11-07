#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-08"
readonly TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PRACTICE_ROOT=$(cd -- "${TASK_DIR}/../.." && pwd)
readonly S3_HELPER="${PRACTICE_ROOT}/tasks/common/s3_fixture.py"
readonly TARGET=/tmp/train_carido_model.py
readonly BUCKET=saved-models
readonly OBJECT_KEY=carido-model.joblib
readonly OWNER_KEY=.ai267-practice-task-08-owner
readonly OWNER_TOKEN="${TASK_STATE_ROOT}/bucket-owner.token"

# Bucket 전체 삭제가 필요한 경우에는 다른 복구를 시작하기 전에 ownership을
# 먼저 증명한다. token 누락/불일치는 fail-closed로 state를 보존한다.
if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/bucket.present" 2>/dev/null || true)" == false ]]; then
  [[ -s "${OWNER_TOKEN}" ]] || {
    printf 'Task 08 cleanup 거부: S3 ownership token이 없습니다.\n' >&2
    exit 1
  }
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/bucket.present" 2>/dev/null || true)" == false ]]; then
  python3 "${S3_HELPER}" delete-owned-bucket \
    "${BUCKET}" "${OWNER_KEY}" "${OWNER_TOKEN}"
elif [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/object.present" 2>/dev/null || true)" == true ]] \
  && [[ -f "${TASK_STATE_ROOT}/original-model.joblib" ]]; then
  python3 "${S3_HELPER}" upload "${BUCKET}" "${OBJECT_KEY}" \
    "${TASK_STATE_ROOT}/original-model.joblib"
elif [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/object.present" 2>/dev/null || true)" == false ]]; then
  python3 "${S3_HELPER}" delete-object "${BUCKET}" "${OBJECT_KEY}"
fi

if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/input.present" 2>/dev/null || true)" == true ]] \
  && [[ -f "${TASK_STATE_ROOT}/original-input.py" ]]; then
  cp -p -- "${TASK_STATE_ROOT}/original-input.py" "${TARGET}"
elif [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/input.present" 2>/dev/null || true)" == false ]]; then
  rm -f -- "${TARGET}"
fi
rm -f -- "${TASK_STATE_ROOT}/input.present" \
  "${TASK_STATE_ROOT}/original-input.py" \
  "${TASK_STATE_ROOT}/bucket.present" \
  "${TASK_STATE_ROOT}/object.present" \
  "${TASK_STATE_ROOT}/original-model.joblib" \
  "${OWNER_TOKEN}"
rmdir "${TASK_STATE_ROOT}" 2>/dev/null || true
