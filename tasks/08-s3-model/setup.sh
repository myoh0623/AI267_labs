#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PRACTICE_ROOT=$(cd -- "${TASK_DIR}/../.." && pwd)
readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-08"
readonly S3_HELPER="${PRACTICE_ROOT}/tasks/common/s3_fixture.py"
readonly TARGET=/tmp/train_carido_model.py
readonly BUCKET=saved-models
readonly OBJECT_KEY=carido-model.joblib
readonly OWNER_KEY=.ai267-practice-task-08-owner
readonly OWNER_TOKEN="${TASK_STATE_ROOT}/bucket-owner.token"

mkdir -p "${TASK_STATE_ROOT}"
chmod 700 "${TASK_STATE_ROOT}"
if [[ -e "${TASK_STATE_ROOT}/input.present" \
  || -e "${TASK_STATE_ROOT}/bucket.present" \
  || -e "${TASK_STATE_ROOT}/object.present" \
  || -e "${OWNER_TOKEN}" ]]; then
  printf 'Task 08 state가 이미 있습니다. 먼저 ai267 finish 08 또는 ai267 reset 08을 실행하세요.\n' >&2
  exit 1
fi
if [[ -e "${TARGET}" ]]; then
  printf 'true\n' > "${TASK_STATE_ROOT}/input.present"
  cp -p -- "${TARGET}" "${TASK_STATE_ROOT}/original-input.py"
else
  printf 'false\n' > "${TASK_STATE_ROOT}/input.present"
fi
cp -- "${TASK_DIR}/inputs/train_carido_model.py" "${TARGET}"

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
    "${TASK_STATE_ROOT}/original-model.joblib"
  python3 "${S3_HELPER}" delete-object "${BUCKET}" "${OBJECT_KEY}"
else
  printf 'false\n' > "${TASK_STATE_ROOT}/object.present"
fi
chmod 600 "${TASK_STATE_ROOT}/input.present" \
  "${TASK_STATE_ROOT}/bucket.present" \
  "${TASK_STATE_ROOT}/object.present"

oc wait --for=condition=Ready pod -n workbench-connections \
  -l notebook-name=workbench-connections-wb --timeout=300s
workbench_pod=$(oc get pod -n workbench-connections \
  -l notebook-name=workbench-connections-wb \
  -o jsonpath='{.items[0].metadata.name}')
oc exec -i -n workbench-connections "${workbench_pod}" \
  -c workbench-connections-wb -- sh -c \
  'cat > /opt/app-root/src/train_carido_model.py' \
  < "${TASK_DIR}/inputs/train_carido_model.py"
