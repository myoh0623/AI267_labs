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

mkdir -p "${TASK_STATE_ROOT}"
chmod 700 "${TASK_STATE_ROOT}"

if [[ -e "${TASK_STATE_ROOT}/bucket.created" \
  || -e "${TASK_STATE_ROOT}/workdir.created" \
  || -e "${TASK_STATE_ROOT}/secret.created" \
  || -e "${OWNER_TOKEN}" ]]; then
  printf 'Task 11 state가 이미 있습니다. 먼저 ai267 finish 11 또는 ai267 reset 11을 실행하세요.\n' >&2
  exit 1
fi
if python3 "${S3_HELPER}" bucket-exists "${BUCKET}"; then
  printf 'Task 11은 빈 saved-models bucket이 필요합니다. 기존 bucket을 먼저 확인하세요.\n' >&2
  exit 1
fi
if [[ -e "${WORK_DIR}" || -L "${WORK_DIR}" ]]; then
  printf '%s가 이미 존재합니다. 기존 연습 파일을 먼저 확인하세요.\n' "${WORK_DIR}" >&2
  exit 1
fi
if oc get secret -n dspa-intro my-s3-connection >/dev/null 2>&1; then
  printf 'dspa-intro/my-s3-connection Secret이 이미 존재합니다. 기존 연결을 먼저 확인하세요.\n' >&2
  exit 1
fi

# 각 marker는 mutation 전에 기록한다. 생성이 중간에 멈춰도 cleanup은
# 실제 task ownership을 검증한 뒤 남은 리소스를 회수한다.
python3 -c 'import secrets; print(secrets.token_hex(32))' > "${OWNER_TOKEN}"
chmod 600 "${OWNER_TOKEN}"
printf 'true\n' > "${TASK_STATE_ROOT}/bucket.created"
chmod 600 "${TASK_STATE_ROOT}/bucket.created"
python3 "${S3_HELPER}" create-bucket "${BUCKET}"
python3 "${S3_HELPER}" upload "${BUCKET}" "${OWNER_KEY}" "${OWNER_TOKEN}"
if ! python3 "${S3_HELPER}" bucket-exists "${BUCKET}"; then
  printf '%s bucket 생성 확인에 실패했습니다.\n' "${BUCKET}" >&2
  exit 1
fi

printf 'true\n' > "${TASK_STATE_ROOT}/workdir.created"
chmod 600 "${TASK_STATE_ROOT}/workdir.created"
mkdir -- "${WORK_DIR}"
printf 'task-11\n' > "${WORK_DIR}/.ai267-task-owned"
chmod 600 "${WORK_DIR}/.ai267-task-owned"
cp -- "${TASK_DIR}/inputs/carido_pipeline.py" "${WORK_DIR}/carido_pipeline.py"

printf 'true\n' > "${TASK_STATE_ROOT}/secret.created"
chmod 600 "${TASK_STATE_ROOT}/secret.created"
oc create -f - <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: my-s3-connection
  namespace: dspa-intro
  annotations:
    opendatahub.io/connection-type: s3
    opendatahub.io/connection-type-protocol: s3
    openshift.io/display-name: my-s3-connection
  labels:
    ai267.practice/created-by: task-11
    opendatahub.io/dashboard: "true"
    opendatahub.io/managed: "true"
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: minio
  AWS_SECRET_ACCESS_KEY: minio123
  AWS_S3_ENDPOINT: https://minio-api-minio.apps.lab.example.com
  AWS_DEFAULT_REGION: us-east-1
  AWS_S3_BUCKET: saved-models
EOF

printf 'Pipeline 입력: %s/carido_pipeline.py\n' "${WORK_DIR}"
