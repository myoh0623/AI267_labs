#!/usr/bin/env bash
set -Eeuo pipefail

readonly LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly LAB_CATALOG="${LAB_ROOT}/tasks/catalog.tsv"
readonly AI267_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}"
readonly AI267_CURRENT_TASK_FILE="${AI267_STATE_ROOT}/current-task"
readonly AI267_LIFECYCLE_LOCK_FILE="${AI267_STATE_ROOT}/lifecycle.lock"

AI267_LIFECYCLE_LOCK_FD=
LAB_COURSE_STATE=
LAB_COURSE_STATUS_OUTPUT=
LAB_COURSE_STATUS_VALUE=
LAB_CURRENT_TASK_VALUE=
LAB_CURRENT_PHASE_VALUE=

lab_log() {
  printf '[ai267] %s\n' "$*"
}

lab_die() {
  printf '[ai267] ERROR: %s\n' "$*" >&2
  exit 1
}

lab_require_command() {
  command -v "$1" >/dev/null 2>&1 || lab_die "필수 명령을 찾을 수 없습니다: $1"
}

lab_require_login() {
  lab_require_command oc
  oc whoami >/dev/null 2>&1 || lab_die 'OpenShift에 먼저 로그인하세요: oc login ...'
}

lab_prepare_state_root() {
  mkdir -p -- "${AI267_STATE_ROOT}" || lab_die "상태 디렉터리를 만들 수 없습니다: ${AI267_STATE_ROOT}"
  [[ -d "${AI267_STATE_ROOT}" && -w "${AI267_STATE_ROOT}" ]] \
    || lab_die "상태 디렉터리에 쓸 수 없습니다: ${AI267_STATE_ROOT}"
}

lab_acquire_lifecycle_lock() {
  lab_require_command flock
  lab_prepare_state_root
  exec {AI267_LIFECYCLE_LOCK_FD}>"${AI267_LIFECYCLE_LOCK_FILE}" \
    || lab_die "수명주기 잠금 파일을 열 수 없습니다: ${AI267_LIFECYCLE_LOCK_FILE}"
  flock -n "${AI267_LIFECYCLE_LOCK_FD}" \
    || lab_die '다른 ai267 start/finish/reset 작업이 실행 중입니다. 완료 후 다시 시도하세요.'
}

lab_normalize_task() {
  local value=${1#0}
  [[ "${value}" =~ ^[0-9]+$ ]] || return 1
  (( value >= 1 && value <= 12 )) || return 1
  printf '%02d\n' "${value}"
}

lab_catalog_row() {
  local task=$1
  awk -F '\t' -v id="${task}" '$1 == id { print; found=1; exit } END { if (!found) exit 1 }' "${LAB_CATALOG}"
}

lab_load_task() {
  local task=$1 row
  row=$(lab_catalog_row "${task}") || lab_die "알 수 없는 문제 번호: ${task}"
  IFS=$'\t' read -r TASK_ID TASK_SLUG TASK_LAB TASK_NAMESPACE TASK_TITLE TASK_POINTS <<<"${row}"
  export TASK_ID TASK_SLUG TASK_LAB TASK_NAMESPACE TASK_TITLE TASK_POINTS
}

lab_task_dir() {
  lab_load_task "$1"
  printf '%s/tasks/%s-%s\n' "${LAB_ROOT}" "${TASK_ID}" "${TASK_SLUG}"
}

lab_list_tasks() {
  printf '번호  공식 Lab                  프로젝트                  문제\n'
  printf '%s\n' '----  ------------------------  ------------------------  ------------------------------'
  while IFS=$'\t' read -r id slug course_lab namespace title points; do
    [[ -n "${id}" && "${id}" != \#* ]] || continue
    printf '%-4s  %-24s  %-24s  %s\n' "${id}" "${course_lab}" "${namespace}" "${title}"
  done < "${LAB_CATALOG}"
}

lab_read_current_state() {
  local -a lines=()
  local task phase
  [[ -e "${AI267_CURRENT_TASK_FILE}" ]] || return 1
  [[ -f "${AI267_CURRENT_TASK_FILE}" ]] || {
    printf '[ai267] ERROR: 현재 Task 상태 파일이 일반 파일이 아닙니다: %s\n' \
      "${AI267_CURRENT_TASK_FILE}" >&2
    return 2
  }
  mapfile -t lines < "${AI267_CURRENT_TASK_FILE}" || {
    printf '[ai267] ERROR: 현재 Task 상태 파일이 비어 있거나 읽을 수 없습니다: %s\n' \
      "${AI267_CURRENT_TASK_FILE}" >&2
    return 2
  }
  task=${lines[0]:-}
  phase=${lines[1]:-legacy}
  if (( ${#lines[@]} > 2 )) \
    || [[ ! "${task}" =~ ^(0[1-9]|1[0-2])$ ]] \
    || [[ ! "${phase}" =~ ^(legacy|starting|setup|active|finishing|resetting|cleanup)$ ]]; then
    printf '[ai267] ERROR: 현재 Task 상태 파일이 손상되었습니다: %s\n' \
      "${AI267_CURRENT_TASK_FILE}" >&2
    return 2
  fi
  LAB_CURRENT_TASK_VALUE=${task}
  LAB_CURRENT_PHASE_VALUE=${phase}
}

lab_current_task() {
  lab_read_current_state || return $?
  printf '%s\n' "${LAB_CURRENT_TASK_VALUE}"
}

lab_current_phase() {
  lab_read_current_state || return $?
  printf '%s\n' "${LAB_CURRENT_PHASE_VALUE}"
}

lab_set_current_task() {
  local task=$1 phase=${2:-active} temporary
  [[ "${task}" =~ ^(0[1-9]|1[0-2])$ ]] || return 2
  [[ "${phase}" =~ ^(starting|setup|active|finishing|resetting|cleanup)$ ]] || return 2
  lab_prepare_state_root
  temporary=$(mktemp "${AI267_STATE_ROOT}/.current-task.XXXXXX") \
    || lab_die '임시 Task 상태 파일을 만들 수 없습니다.'
  if ! chmod 600 "${temporary}" || ! printf '%s\n%s\n' "${task}" "${phase}" > "${temporary}"; then
    rm -f -- "${temporary}"
    lab_die 'Task 상태를 기록할 수 없습니다.'
  fi
  if ! mv -f -- "${temporary}" "${AI267_CURRENT_TASK_FILE}"; then
    rm -f -- "${temporary}"
    lab_die 'Task 상태를 원자적으로 저장할 수 없습니다.'
  fi
}

lab_set_current_phase() {
  local phase=$1
  lab_read_current_state || return $?
  lab_set_current_task "${LAB_CURRENT_TASK_VALUE}" "${phase}"
}

lab_clear_current_task() {
  rm -f -- "${AI267_CURRENT_TASK_FILE}"
}

lab_course_status() {
  local course_lab=$1
  (cd "${HOME}" && lab status "${course_lab}") 2>&1
}

lab_query_course_state() {
  local course_lab=$1 output rc=0 line status_value= normalized
  local status_pattern='Status:[[:space:]]*(Not[[:space:]]+Started|Started|Attempted|Clean|Finished|Stopped|Starting|Stopping|Finishing|Resetting)([[:space:](]|$)'
  if output=$(lab_course_status "${course_lab}"); then
    rc=0
  else
    rc=$?
  fi

  LAB_COURSE_STATUS_OUTPUT=${output}
  LAB_COURSE_STATUS_VALUE=
  LAB_COURSE_STATE=
  if (( rc != 0 )); then
    printf '[ai267] ERROR: lab status %s 명령이 실패했습니다 (rc=%s).\n' \
      "${course_lab}" "${rc}" >&2
    [[ -z "${output}" ]] || printf '%s\n' "${output}" >&2
    return 2
  fi

  while IFS= read -r line; do
    if [[ "${line}" =~ ${status_pattern} ]]; then
      status_value=${BASH_REMATCH[1]}
    fi
  done <<< "${output}"
  status_value=${status_value%$'\r'}
  status_value=${status_value#"${status_value%%[![:space:]]*}"}
  status_value=${status_value%"${status_value##*[![:space:]]}"}
  LAB_COURSE_STATUS_VALUE=${status_value}
  normalized=${status_value,,}

  case "${normalized}" in
    started)
      LAB_COURSE_STATE=started
      ;;
    clean|finished|stopped|not\ started|not-started)
      LAB_COURSE_STATE=terminal
      ;;
    starting|stopping|finishing|resetting)
      LAB_COURSE_STATE=transitional
      ;;
    attempted)
      LAB_COURSE_STATE=recoverable
      ;;
    *)
      printf '[ai267] ERROR: lab status %s에서 알 수 없는 상태를 받았습니다: %s\n' \
        "${course_lab}" "${status_value:-<missing>}" >&2
      [[ -z "${output}" ]] || printf '%s\n' "${output}" >&2
      return 2
      ;;
  esac
}

lab_course_started() {
  lab_query_course_state "$1" || return 2
  [[ "${LAB_COURSE_STATE}" == started ]]
}

lab_wait_course_started() {
  local course_lab=$1 attempt
  local attempts=${AI267_STATUS_ATTEMPTS:-30}
  local interval=${AI267_STATUS_INTERVAL_SECONDS:-2}
  [[ "${attempts}" =~ ^[1-9][0-9]*$ ]] \
    || { printf '[ai267] ERROR: AI267_STATUS_ATTEMPTS 값이 올바르지 않습니다.\n' >&2; return 2; }
  [[ "${interval}" =~ ^[0-9]+([.][0-9]+)?$ ]] \
    || { printf '[ai267] ERROR: AI267_STATUS_INTERVAL_SECONDS 값이 올바르지 않습니다.\n' >&2; return 2; }

  for (( attempt = 1; attempt <= attempts; attempt++ )); do
    lab_query_course_state "${course_lab}" || return 2
    case "${LAB_COURSE_STATE}" in
      started) return 0 ;;
      terminal) return 1 ;;
    esac
    (( attempt == attempts )) || sleep "${interval}"
  done
  printf '[ai267] ERROR: %s이 Started 상태가 되기를 기다리다 시간 초과했습니다.\n' \
    "${course_lab}" >&2
  return 1
}

lab_wait_course_terminal() {
  local course_lab=$1 attempt
  local attempts=${AI267_STATUS_ATTEMPTS:-30}
  local interval=${AI267_STATUS_INTERVAL_SECONDS:-2}
  [[ "${attempts}" =~ ^[1-9][0-9]*$ ]] \
    || { printf '[ai267] ERROR: AI267_STATUS_ATTEMPTS 값이 올바르지 않습니다.\n' >&2; return 2; }
  [[ "${interval}" =~ ^[0-9]+([.][0-9]+)?$ ]] \
    || { printf '[ai267] ERROR: AI267_STATUS_INTERVAL_SECONDS 값이 올바르지 않습니다.\n' >&2; return 2; }

  for (( attempt = 1; attempt <= attempts; attempt++ )); do
    lab_query_course_state "${course_lab}" || return 2
    [[ "${LAB_COURSE_STATE}" == terminal ]] && return 0
    (( attempt == attempts )) || sleep "${interval}"
  done
  printf '[ai267] ERROR: %s의 종료 상태를 기다리다 시간 초과했습니다 (마지막 상태: %s).\n' \
    "${course_lab}" "${LAB_COURSE_STATUS_VALUE:-unknown}" >&2
  return 1
}

lab_wait_course_stopped() {
  lab_wait_course_terminal "$@"
}

lab_active_course_labs() {
  local course_lab course_labs
  if ! course_labs=$(awk -F '\t' '!/^#/ && NF >= 3 { print $3 }' "${LAB_CATALOG}" | sort -u); then
    printf '[ai267] ERROR: 공식 Lab 목록을 읽을 수 없습니다.\n' >&2
    return 2
  fi
  while IFS= read -r course_lab; do
    [[ -n "${course_lab}" ]] || continue
    lab_query_course_state "${course_lab}" || return 2
    if [[ "${LAB_COURSE_STATE}" != terminal ]]; then
      printf '%s\n' "${course_lab}"
    fi
  done <<< "${course_labs}"
}

lab_run_hook() {
  local task=$1 hook=$2 task_dir hook_path
  task_dir=$(lab_task_dir "${task}")
  hook_path="${task_dir}/${hook}.sh"
  [[ -f "${hook_path}" ]] || return 0
  lab_log "Task ${task} ${hook} hook"
  bash "${hook_path}"
}

lab_print_task() {
  local task_dir
  task_dir=$(lab_task_dir "$1")
  printf '\n'
  sed -n '1,300p' "${task_dir}/README.md"
}
