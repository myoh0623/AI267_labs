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

mkdir -p "${TASK_STATE_ROOT}"
chmod 700 "${TASK_STATE_ROOT}"
if [[ -e "${TASK_STATE_ROOT}/tiger.present" \
  || -e "${TASK_STATE_ROOT}/bucket.present" \
  || -e "${TASK_STATE_ROOT}/object.present" \
  || -e "${OWNER_TOKEN}" ]]; then
  printf 'Task 09 state가 이미 있습니다. 먼저 ai267 finish 09 또는 ai267 reset 09를 실행하세요.\n' >&2
  exit 1
fi

if oc get namespace tiger >/dev/null 2>&1; then
  printf 'Task 09는 빈 상태의 tiger 프로젝트가 필요합니다. 기존 프로젝트를 먼저 확인하세요.\n' >&2
  exit 1
fi
printf 'false\n' > "${TASK_STATE_ROOT}/tiger.present"

if python3 "${S3_HELPER}" bucket-exists "${BUCKET}"; then
  printf 'true\n' > "${TASK_STATE_ROOT}/bucket.present"
else
  printf 'false\n' > "${TASK_STATE_ROOT}/bucket.present"
  python3 -c 'import secrets; print(secrets.token_hex(32))' > "${OWNER_TOKEN}"
  chmod 600 "${OWNER_TOKEN}"
  python3 "${S3_HELPER}" create-bucket "${BUCKET}"
  python3 "${S3_HELPER}" upload "${BUCKET}" "${OWNER_KEY}" "${OWNER_TOKEN}"
fi

if python3 "${S3_HELPER}" object-exists "${BUCKET}" "${OBJECT_KEY}"; then
  printf 'true\n' > "${TASK_STATE_ROOT}/object.present"
  python3 "${S3_HELPER}" download "${BUCKET}" "${OBJECT_KEY}" \
    "${TASK_STATE_ROOT}/original-model.onnx"
else
  printf 'false\n' > "${TASK_STATE_ROOT}/object.present"
fi
chmod 600 "${TASK_STATE_ROOT}/tiger.present" \
  "${TASK_STATE_ROOT}/bucket.present" \
  "${TASK_STATE_ROOT}/object.present"

base64 --decode "${TASK_DIR}/inputs/diabetes-model.onnx.b64" \
  > "${TASK_STATE_ROOT}/diabetes-model.onnx"
python3 "${S3_HELPER}" upload "${BUCKET}" "${OBJECT_KEY}" \
  "${TASK_STATE_ROOT}/diabetes-model.onnx"

printf '합성 ONNX 입력 준비: s3://%s/%s\n' "${BUCKET}" "${OBJECT_KEY}"
