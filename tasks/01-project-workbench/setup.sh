#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-01"
readonly PROJECT=my-lab-pro
readonly PROFILE_NAMESPACE=redhat-ods-applications
readonly PROFILE=task01-2cpu-8gi

mkdir -p "${TASK_STATE_ROOT}"
chmod 700 "${TASK_STATE_ROOT}"

if [[ -e "${TASK_STATE_ROOT}/project.absent-at-start" || -e "${TASK_STATE_ROOT}/profile.created" ]]; then
  printf 'Task 01 state가 이미 있습니다. 먼저 ai267 finish 01을 실행하세요.\n' >&2
  exit 1
fi
if oc get namespace "${PROJECT}" >/dev/null 2>&1; then
  printf '%s 프로젝트가 이미 존재합니다. 기존 리소스를 보호하기 위해 시작하지 않습니다.\n' "${PROJECT}" >&2
  exit 1
fi
if oc get hardwareprofile.infrastructure.opendatahub.io "${PROFILE}" \
  -n "${PROFILE_NAMESPACE}" >/dev/null 2>&1; then
  printf '%s/%s HardwareProfile이 이미 존재합니다.\n' "${PROFILE_NAMESPACE}" "${PROFILE}" >&2
  exit 1
fi

printf 'true\n' > "${TASK_STATE_ROOT}/project.absent-at-start"
: > "${TASK_STATE_ROOT}/created-users.txt"
chmod 600 "${TASK_STATE_ROOT}/project.absent-at-start" \
  "${TASK_STATE_ROOT}/created-users.txt"

for practice_user in suraj rajan punit; do
  if ! oc get user.user.openshift.io "${practice_user}" >/dev/null 2>&1; then
    oc create user "${practice_user}"
    printf '%s\n' "${practice_user}" >> "${TASK_STATE_ROOT}/created-users.txt"
  fi
done

# preflight에서 부재를 확인했다. mutation 전에 marker를 기록해 create 도중
# 중단되더라도 cleanup이 task-owned profile을 회수할 수 있게 한다.
printf 'true\n' > "${TASK_STATE_ROOT}/profile.created"
chmod 600 "${TASK_STATE_ROOT}/profile.created"
oc create -f - <<'EOF'
apiVersion: infrastructure.opendatahub.io/v1
kind: HardwareProfile
metadata:
  name: task01-2cpu-8gi
  namespace: redhat-ods-applications
  labels:
    ai267.practice/created-by: task-01
  annotations:
    opendatahub.io/disabled: "false"
    opendatahub.io/display-name: Task 01 - 2 CPU, 8 GiB
spec:
  identifiers:
    - identifier: cpu
      displayName: CPU
      resourceType: CPU
      minCount: "2"
      defaultCount: "2"
      maxCount: "2"
    - identifier: memory
      displayName: Memory
      resourceType: Memory
      minCount: 8Gi
      defaultCount: 8Gi
      maxCount: 8Gi
EOF

printf '준비 완료: my-lab-pro 프로젝트는 직접 생성하세요.\n'
