#!/usr/bin/env bash
set -Eeuo pipefail

readonly TEST_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly TEST_TMP=$(mktemp -d)
readonly REAL_PYTHON3=$(command -v python3)
trap 'rm -rf -- "${TEST_TMP}"' EXIT

readonly FAKE_BIN="${TEST_TMP}/bin"
export HOME="${TEST_TMP}/home"
export AI267_STATE_ROOT="${TEST_TMP}/state"
export FAKE_LAB_STATE_ROOT="${TEST_TMP}/lab-state"
export FAKE_LAB_LOG="${TEST_TMP}/lab.log"
export FAKE_OC_LOG="${TEST_TMP}/oc.log"
export FAKE_EVENT_LOG="${TEST_TMP}/events.log"
export AI267_STATUS_ATTEMPTS=3
export AI267_STATUS_INTERVAL_SECONDS=0

mkdir -p "${FAKE_BIN}" "${HOME}" "${AI267_STATE_ROOT}" "${FAKE_LAB_STATE_ROOT}"
: > "${FAKE_LAB_LOG}"
: > "${FAKE_OC_LOG}"
: > "${FAKE_EVENT_LOG}"

cat > "${FAKE_BIN}/lab" <<'FAKE_LAB'
#!/usr/bin/env bash
set -u

command_name=${1:-}
course_lab=${2:-}
state_file="${FAKE_LAB_STATE_ROOT}/${course_lab}"

read_state() {
  if [[ -f "${state_file}" ]]; then
    sed -n '1p' "${state_file}"
  else
    printf 'Clean\n'
  fi
}

print_status() {
  local state=$1 suffix=
  [[ "${state}" == Started ]] && suffix=' (running successfully)'
  [[ "${state}" == Attempted ]] && suffix=' (failed or interrupted)'
  printf "📊 Lab '%s' Status: %s%s\n" "${course_lab}" "${state}" "${suffix}"
}

case "${command_name}" in
  status)
    if [[ "${FAKE_STATUS_ERROR:-0}" == 1 ]]; then
      printf 'simulated status transport error\n' >&2
      exit 42
    fi
    if [[ "${3:-}" == --reset ]]; then
      printf 'forbidden-status-reset %s\n' "${course_lab}" >> "${FAKE_LAB_LOG}"
      printf 'status --reset must not be used for resource cleanup\n' >&2
      exit 99
    fi
    if [[ -n "${FAKE_STATUS_VALUE:-}" ]]; then
      print_status "${FAKE_STATUS_VALUE}"
    else
      print_status "$(read_state)"
    fi
    ;;
  start)
    printf 'start %s\n' "${course_lab}" >> "${FAKE_LAB_LOG}"
    printf 'lab-start %s\n' "${course_lab}" >> "${FAKE_EVENT_LOG}"
    if [[ "${FAKE_START_NO_STATE:-0}" != 1 ]]; then
      printf 'Started\n' > "${state_file}"
    fi
    sleep "${FAKE_START_SLEEP:-0}"
    exit "${FAKE_START_RC:-0}"
    ;;
  finish)
    printf 'finish %s\n' "${course_lab}" >> "${FAKE_LAB_LOG}"
    printf 'lab-finish %s\n' "${course_lab}" >> "${FAKE_EVENT_LOG}"
    if [[ "${FAKE_FINISH_STUCK:-0}" != 1 ]]; then
      printf 'Finished\n' > "${state_file}"
    fi
    print_status "$(read_state)"
    exit "${FAKE_FINISH_RC:-0}"
    ;;
  *)
    printf 'unexpected fake lab invocation: %s\n' "$*" >&2
    exit 64
    ;;
esac
FAKE_LAB

cat > "${FAKE_BIN}/oc" <<'FAKE_OC'
#!/usr/bin/env bash
set -u

printf '%s\n' "$*" >> "${FAKE_OC_LOG}"
if [[ "${1:-}" == whoami ]]; then
  printf 'system:admin\n'
  exit 0
fi
if [[ "${1:-}" == get && "${2:-}" == namespace \
  && ( "${3:-}" == my-lab-pro || "${3:-}" == projects-data ) ]]; then
  exit 1
fi
if [[ "${1:-}" == get \
  && "${2:-}" == hardwareprofile.infrastructure.opendatahub.io \
  && "${3:-}" == task01-2cpu-8gi ]]; then
  exit 1
fi
if [[ "${1:-}" == get && "${2:-}" == user.user.openshift.io ]]; then
  case "${3:-}" in
    suraj|rajan|punit) exit 1 ;;
  esac
fi
if [[ "${1:-}" == delete && "${2:-}" == user.user.openshift.io \
  && "${FAKE_OC_DELETE_FAIL:-0}" == 1 ]]; then
  printf 'simulated user cleanup failure\n' >&2
  exit 7
fi
exit 0
FAKE_OC

cat > "${FAKE_BIN}/python3" <<'FAKE_PYTHON'
#!/usr/bin/env bash
set -u

if [[ "${1:-}" == */tasks/common/s3_fixture.py ]]; then
  printf 's3 %s %s\n' "${2:-}" "${3:-}" >> "${FAKE_EVENT_LOG}"
  case "${2:-}" in
    bucket-exists) exit 1 ;;
    purge-bucket)
      [[ "${FAKE_S3_DELETE_FAIL:-0}" == 1 ]] && exit 8
      exit 0
      ;;
    create-bucket|upload|delete-bucket|delete-owned-bucket) exit 0 ;;
  esac
fi
exec "${REAL_PYTHON3}" "$@"
FAKE_PYTHON

export REAL_PYTHON3
chmod +x "${FAKE_BIN}/lab" "${FAKE_BIN}/oc" "${FAKE_BIN}/python3"
export PATH="${FAKE_BIN}:${PATH}"

fail() {
  printf '[lifecycle-test] FAIL: %s\n' "$*" >&2
  exit 1
}

run_ok() {
  local output_file=$1
  shift
  "$@" > "${output_file}" 2>&1 \
    || { sed -n '1,240p' "${output_file}" >&2; fail "expected success: $*"; }
}

run_fail() {
  local output_file=$1
  shift
  if "$@" > "${output_file}" 2>&1; then
    sed -n '1,240p' "${output_file}" >&2
    fail "expected failure: $*"
  fi
}

assert_contains() {
  local needle=$1 file=$2
  grep -Fq -- "${needle}" "${file}" \
    || { sed -n '1,240p' "${file}" >&2; fail "missing '${needle}' in ${file}"; }
}

assert_not_contains() {
  local needle=$1 file=$2
  if grep -Fq -- "${needle}" "${file}"; then
    sed -n '1,240p' "${file}" >&2
    fail "unexpected '${needle}' in ${file}"
  fi
}

assert_before() {
  local earlier=$1 later=$2 file=$3 earlier_line later_line
  earlier_line=$(grep -nF -- "${earlier}" "${file}" | head -n 1 | cut -d: -f1)
  later_line=$(grep -nF -- "${later}" "${file}" | head -n 1 | cut -d: -f1)
  [[ -n "${earlier_line}" && -n "${later_line}" && ${earlier_line} -lt ${later_line} ]] \
    || { sed -n '1,240p' "${file}" >&2; fail "expected '${earlier}' before '${later}'"; }
}

assert_marker() {
  local task=$1 phase=$2
  [[ -f "${AI267_STATE_ROOT}/current-task" ]] || fail 'current-task marker is missing'
  [[ "$(sed -n '1p' "${AI267_STATE_ROOT}/current-task")" == "${task}" ]] \
    || fail 'unexpected marker task'
  [[ "$(sed -n '2p' "${AI267_STATE_ROOT}/current-task")" == "${phase}" ]] \
    || fail 'unexpected marker phase'
  [[ "$(stat -c '%a' "${AI267_STATE_ROOT}/current-task")" == 600 ]] \
    || fail 'current-task marker permissions are not 600'
}

assert_no_marker() {
  [[ ! -e "${AI267_STATE_ROOT}/current-task" ]] || fail 'current-task marker was not cleared'
}

readonly COURSE_LAB="${TEST_ROOT}/scripts/course-lab.sh"

printf '[lifecycle-test] argc validation\n'
run_fail "${TEST_TMP}/argc.out" bash "${COURSE_LAB}" start
assert_contains '사용법:' "${TEST_TMP}/argc.out"
if grep -Fq 'unbound variable' "${TEST_TMP}/argc.out"; then
  fail 'argc failure leaked an unbound-variable error'
fi

printf '[lifecycle-test] real lab status fixture and status error fail-closed\n'
run_ok "${TEST_TMP}/start-04.out" bash "${COURSE_LAB}" start 04
assert_marker 04 active
run_ok "${TEST_TMP}/start-04-idempotent.out" bash "${COURSE_LAB}" start 04
assert_contains '이미 실행 중입니다' "${TEST_TMP}/start-04-idempotent.out"
assert_marker 04 active
run_fail "${TEST_TMP}/grade-fail.out" bash "${COURSE_LAB}" finish 04
assert_marker 04 active
[[ "$(sed -n '1p' "${FAKE_LAB_STATE_ROOT}/workbench-connections")" == Started ]] \
  || fail 'failed grading changed the official lab state'
export FAKE_STATUS_ERROR=1
run_fail "${TEST_TMP}/status-error.out" bash "${COURSE_LAB}" reset 04
assert_marker 04 resetting
[[ "$(sed -n '1p' "${FAKE_LAB_STATE_ROOT}/workbench-connections")" == Started ]] \
  || fail 'status failure changed the official lab state'
unset FAKE_STATUS_ERROR
: > "${FAKE_EVENT_LOG}"
run_ok "${TEST_TMP}/reset-04.out" bash "${COURSE_LAB}" reset 04
assert_before 's3 purge-bucket projects-data-bucket' \
  'lab-finish workbench-connections' "${FAKE_EVENT_LOG}"
assert_no_marker

printf '[lifecycle-test] live dependency cleanup fails before official lab finish\n'
run_ok "${TEST_TMP}/s3-fail-start.out" bash "${COURSE_LAB}" start 04
: > "${FAKE_EVENT_LOG}"
export FAKE_S3_DELETE_FAIL=1
run_fail "${TEST_TMP}/s3-fail-reset.out" bash "${COURSE_LAB}" reset 04
assert_marker 04 cleanup
assert_not_contains 'lab-finish workbench-connections' "${FAKE_EVENT_LOG}"
[[ "$(sed -n '1p' "${FAKE_LAB_STATE_ROOT}/workbench-connections")" == Started ]] \
  || fail 'cleanup failure did not preserve the official lab'
unset FAKE_S3_DELETE_FAIL
run_ok "${TEST_TMP}/s3-fail-retry.out" bash "${COURSE_LAB}" reset 04
assert_no_marker

printf '[lifecycle-test] cleanup hook failure preserves recovery state\n'
run_ok "${TEST_TMP}/start-01.out" bash "${COURSE_LAB}" start 01
export FAKE_OC_DELETE_FAIL=1
run_fail "${TEST_TMP}/cleanup-error.out" bash "${COURSE_LAB}" reset 01
assert_marker 01 cleanup
assert_contains 'cleanup hook이 실패했습니다' "${TEST_TMP}/cleanup-error.out"
unset FAKE_OC_DELETE_FAIL
run_ok "${TEST_TMP}/cleanup-retry.out" bash "${COURSE_LAB}" reset 01
assert_no_marker

printf '[lifecycle-test] partial start failure keeps a starting-phase recovery marker\n'
: > "${FAKE_OC_LOG}"
export FAKE_START_RC=9
run_fail "${TEST_TMP}/partial-start.out" bash "${COURSE_LAB}" start 01
assert_marker 01 starting
unset FAKE_START_RC
run_fail "${TEST_TMP}/partial-start-repeat.out" bash "${COURSE_LAB}" start 01
assert_contains '복구 단계에 있습니다 (starting)' "${TEST_TMP}/partial-start-repeat.out"
assert_marker 01 starting
run_ok "${TEST_TMP}/partial-reset.out" bash "${COURSE_LAB}" reset 01
assert_no_marker
if grep -Fq 'delete user.user.openshift.io' "${FAKE_OC_LOG}"; then
  fail 'reset invoked cleanup hook although setup never started'
fi

printf '[lifecycle-test] flock rejects concurrent lifecycle mutation\n'
: > "${FAKE_LAB_LOG}"
export FAKE_START_SLEEP=1
bash "${COURSE_LAB}" start 04 > "${TEST_TMP}/concurrent-first.out" 2>&1 &
first_pid=$!
start_seen=false
for _ in {1..40}; do
  if grep -Fq 'start workbench-connections' "${FAKE_LAB_LOG}"; then
    start_seen=true
    break
  fi
  sleep 0.05
done
[[ "${start_seen}" == true ]] || fail 'first concurrent start did not reach fake lab'
run_fail "${TEST_TMP}/concurrent-second.out" bash "${COURSE_LAB}" start 05
assert_contains '다른 ai267 start/finish/reset 작업' "${TEST_TMP}/concurrent-second.out"
wait "${first_pid}" \
  || { sed -n '1,240p' "${TEST_TMP}/concurrent-first.out" >&2; fail 'first concurrent start failed'; }
unset FAKE_START_SLEEP
run_ok "${TEST_TMP}/concurrent-reset.out" bash "${COURSE_LAB}" reset 04
assert_no_marker

printf '[lifecycle-test] nonterminal finish preserves state and never uses status --reset\n'
run_ok "${TEST_TMP}/stuck-start.out" bash "${COURSE_LAB}" start 04
: > "${FAKE_LAB_LOG}"
export FAKE_FINISH_STUCK=1
run_fail "${TEST_TMP}/stuck-reset.out" bash "${COURSE_LAB}" reset 04
assert_marker 04 cleanup
assert_contains 'finish workbench-connections' "${FAKE_LAB_LOG}"
assert_not_contains 'forbidden-status-reset' "${FAKE_LAB_LOG}"
[[ "$(sed -n '1p' "${FAKE_LAB_STATE_ROOT}/workbench-connections")" == Started ]] \
  || fail 'failed finish unexpectedly changed the official lab state'
unset FAKE_FINISH_STUCK
run_ok "${TEST_TMP}/stuck-retry.out" bash "${COURSE_LAB}" reset 04
assert_no_marker

printf '[lifecycle-test] Attempted status is recoverable through lab finish\n'
run_ok "${TEST_TMP}/attempted-start.out" bash "${COURSE_LAB}" start 04
printf 'Attempted\n' > "${FAKE_LAB_STATE_ROOT}/workbench-connections"
run_fail "${TEST_TMP}/attempted-repeat.out" bash "${COURSE_LAB}" start 04
assert_contains '공식 Lab이 Attempted 상태입니다' "${TEST_TMP}/attempted-repeat.out"
: > "${FAKE_LAB_LOG}"
run_ok "${TEST_TMP}/attempted-reset.out" bash "${COURSE_LAB}" reset 04
assert_contains 'finish workbench-connections' "${FAKE_LAB_LOG}"
assert_not_contains 'forbidden-status-reset' "${FAKE_LAB_LOG}"
assert_no_marker

printf '[lifecycle-test] same-task start is idempotent only in active or legacy phase\n'
run_ok "${TEST_TMP}/phase-start.out" bash "${COURSE_LAB}" start 04
printf '04\n' > "${AI267_STATE_ROOT}/current-task"
chmod 600 "${AI267_STATE_ROOT}/current-task"
run_ok "${TEST_TMP}/legacy-repeat.out" bash "${COURSE_LAB}" start 04
assert_contains '이미 실행 중입니다' "${TEST_TMP}/legacy-repeat.out"
for recovery_phase in starting setup finishing resetting cleanup; do
  printf '04\n%s\n' "${recovery_phase}" > "${AI267_STATE_ROOT}/current-task"
  chmod 600 "${AI267_STATE_ROOT}/current-task"
  run_fail "${TEST_TMP}/phase-${recovery_phase}.out" bash "${COURSE_LAB}" start 04
  assert_contains "복구 단계에 있습니다 (${recovery_phase})" "${TEST_TMP}/phase-${recovery_phase}.out"
done
run_ok "${TEST_TMP}/phase-reset.out" bash "${COURSE_LAB}" reset 04
assert_no_marker

printf '[lifecycle-test] PASS\n'
