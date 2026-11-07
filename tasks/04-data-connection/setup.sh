#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PRACTICE_ROOT=$(cd -- "${TASK_DIR}/../.." && pwd)
readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-04"
readonly S3_HELPER="${PRACTICE_ROOT}/tasks/common/s3_fixture.py"
readonly PROJECT=projects-data
readonly BUCKET=projects-data-bucket

mkdir -p "${TASK_STATE_ROOT}"
chmod 700 "${TASK_STATE_ROOT}"

if [[ -e "${TASK_STATE_ROOT}/project.created" || -e "${TASK_STATE_ROOT}/bucket.absent-at-start" ]]; then
  printf 'Task 04 state가 이미 있습니다. 먼저 ai267 finish 04를 실행하세요.\n' >&2
  exit 1
fi
if oc get namespace "${PROJECT}" >/dev/null 2>&1; then
  printf '%s 프로젝트가 이미 존재합니다. 기존 리소스를 먼저 확인하세요.\n' "${PROJECT}" >&2
  exit 1
fi
if python3 "${S3_HELPER}" bucket-exists "${BUCKET}"; then
  printf '%s bucket이 이미 존재합니다. 기존 객체를 보호하기 위해 시작하지 않습니다.\n' "${BUCKET}" >&2
  exit 1
fi
printf 'true\n' > "${TASK_STATE_ROOT}/bucket.absent-at-start"
printf 'true\n' > "${TASK_STATE_ROOT}/project.created"
chmod 600 "${TASK_STATE_ROOT}/bucket.absent-at-start" \
  "${TASK_STATE_ROOT}/project.created"

oc new-project "${PROJECT}" >/dev/null
oc label namespace "${PROJECT}" ai267.practice/created-by=task-04 --overwrite
oc adm policy add-role-to-user admin developer -n "${PROJECT}" >/dev/null

printf '준비 완료: %s 프로젝트. bucket, Connection, Workbench는 직접 생성하세요.\n' "${PROJECT}"
