#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-12"
readonly NAMESPACE=dspa-elyra
readonly SOURCE_SECRET=s3-minio
readonly COMPAT_SECRET=aws-connection-s3-minio

mkdir -p "${TASK_STATE_ROOT}"
chmod 700 "${TASK_STATE_ROOT}"

if [[ -e "${TASK_STATE_ROOT}/compat-secret.created" ]]; then
  printf 'Task 12 state가 이미 있습니다. 먼저 ai267 finish 12 또는 ai267 reset 12를 실행하세요.\n' >&2
  exit 1
fi

if oc get secret "${COMPAT_SECRET}" -n "${NAMESPACE}" >/dev/null 2>&1; then
  oc get secret "${COMPAT_SECRET}" -n "${NAMESPACE}" -o json \
    | python3 -c '
import json, sys
required = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT", "AWS_S3_BUCKET")
data = json.load(sys.stdin).get("data", {})
missing = [key for key in required if not data.get(key)]
if missing:
    raise SystemExit("compatibility Secret missing keys: " + ", ".join(missing))
'
  if oc get secret "${SOURCE_SECRET}" -n "${NAMESPACE}" >/dev/null 2>&1; then
    python3 - \
      <(oc get secret "${SOURCE_SECRET}" -n "${NAMESPACE}" -o json) \
      <(oc get secret "${COMPAT_SECRET}" -n "${NAMESPACE}" -o json) <<'PY'
import json
import sys

required = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT", "AWS_S3_BUCKET")
with open(sys.argv[1], encoding="utf-8") as source_stream:
    source = json.load(source_stream).get("data", {})
with open(sys.argv[2], encoding="utf-8") as compat_stream:
    compat = json.load(compat_stream).get("data", {})
if any(source.get(key) != compat.get(key) for key in required):
    raise SystemExit("existing compatibility Secret does not match s3-minio")
PY
  fi
  printf 'false\n' > "${TASK_STATE_ROOT}/compat-secret.created"
  printf '준비 완료: 공식 Lab의 %s Secret을 그대로 사용합니다.\n' "${COMPAT_SECRET}"
  exit 0
fi

for _ in {1..30}; do
  oc get secret "${SOURCE_SECRET}" -n "${NAMESPACE}" >/dev/null 2>&1 && break
  sleep 2
done
oc get secret "${SOURCE_SECRET}" -n "${NAMESPACE}" >/dev/null 2>&1 || {
  printf '공식 Lab의 %s Secret을 찾을 수 없습니다.\n' "${SOURCE_SECRET}" >&2
  exit 1
}

# cleanup이 중간 실패에서도 task-owned Secret만 회수할 수 있도록 mutation 전에 marker를 기록한다.
printf 'true\n' > "${TASK_STATE_ROOT}/compat-secret.created"
oc get secret "${SOURCE_SECRET}" -n "${NAMESPACE}" -o json \
  | python3 -c '
import json, sys

source = json.load(sys.stdin)
required = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT", "AWS_S3_BUCKET")
data = source.get("data", {})
missing = [key for key in required if not data.get(key)]
if missing:
    raise SystemExit("source Secret missing keys: " + ", ".join(missing))
json.dump({
    "apiVersion": "v1",
    "kind": "Secret",
    "metadata": {
        "name": "aws-connection-s3-minio",
        "namespace": "dspa-elyra",
        "labels": {"ai267.practice/created-by": "task-12"},
    },
    "type": "Opaque",
    "data": {key: data[key] for key in required},
}, sys.stdout)
' \
  | oc create -f - >/dev/null

printf '준비 완료: namespace/DSPA/S3 입력과 원문 Secret 호환 fixture만 제공했습니다.\n'
printf 'pipelines-elyra-wb, Runtime Image, pipeline graph는 직접 만드세요.\n'
