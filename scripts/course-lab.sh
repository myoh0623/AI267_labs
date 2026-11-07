#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

if (( $# != 2 )); then
  lab_die '사용법: course-lab.sh <start|finish|reset> <01-12>'
fi

action=$1
case "${action}" in
  start|finish|reset) ;;
  *) lab_die "지원하지 않는 동작: ${action}" ;;
esac
task=$(lab_normalize_task "$2") \
  || lab_die '문제 번호는 01부터 12까지 입력하세요.'

lab_load_task "${task}"
lab_require_command lab
lab_require_login
lab_acquire_lifecycle_lock

CURRENT_TASK=
CURRENT_PHASE=

load_current_state() {
  local rc
  if lab_read_current_state; then
    CURRENT_TASK=${LAB_CURRENT_TASK_VALUE}
    CURRENT_PHASE=${LAB_CURRENT_PHASE_VALUE}
    return 0
  else
    rc=$?
  fi
  if (( rc == 1 )); then
    CURRENT_TASK=
    CURRENT_PHASE=
    return 0
  fi
  lab_die "상태 파일을 복구하거나 삭제한 뒤 다시 시도하세요: ${AI267_CURRENT_TASK_FILE}"
}

require_current_task() {
  load_current_state
  [[ "${CURRENT_TASK}" == "${task}" ]] || {
    if [[ -n "${CURRENT_TASK}" ]]; then
      lab_die "Task ${CURRENT_TASK}이 실행 중입니다. 먼저 'ai267 finish ${CURRENT_TASK}' 또는 'ai267 reset ${CURRENT_TASK}'을 실행하세요."
    fi
    lab_die "Task ${task}이 시작되지 않았습니다. 먼저 'ai267 ${task}'을 실행하세요."
  }
}

print_command_output() {
  local output=$1
  [[ -z "${output}" ]] || printf '%s\n' "${output}"
}

finish_course_lab() {
  local output rc=0 wait_rc
  lab_query_course_state "${TASK_LAB}" || return 2
  [[ "${LAB_COURSE_STATE}" == terminal ]] && return 0

  if output=$(cd "${HOME}" && lab finish "${TASK_LAB}" 2>&1); then
    rc=0
  else
    rc=$?
  fi
  print_command_output "${output}"

  if lab_wait_course_terminal "${TASK_LAB}"; then
    if (( rc != 0 )); then
      lab_log "lab finish가 rc=${rc}을 반환했지만 ${TASK_LAB}의 종료 상태를 확인했습니다."
    fi
    return 0
  else
    wait_rc=$?
  fi
  return "${wait_rc}"
}

cleanup_hook_required() {
  [[ "${CURRENT_PHASE}" != starting ]]
}

# These fixtures use the MinIO service brought up for the course lab.  Restore
# them while that dependency is still available; all other hooks keep the
# default post-finish order.
cleanup_requires_running_lab() {
  case "${task}" in
    04|08|09|11) return 0 ;;
    *) return 1 ;;
  esac
}

run_cleanup_hook() {
  lab_set_current_phase cleanup
  CURRENT_PHASE=cleanup
  lab_run_hook "${task}" cleanup
}

case "${action}" in
  start)
    load_current_state
    if [[ "${CURRENT_TASK}" == "${task}" ]]; then
      case "${CURRENT_PHASE}" in
        active|legacy) ;;
        *)
          lab_die "Task ${task}이 복구 단계에 있습니다 (${CURRENT_PHASE}). start를 반복하지 말고 'ai267 reset ${task}'을 실행하세요."
          ;;
      esac
      lab_query_course_state "${TASK_LAB}" \
        || lab_die "${TASK_LAB} 상태를 확인할 수 없어 기존 Task 상태를 보존합니다."
      case "${LAB_COURSE_STATE}" in
        started)
          lab_log "Task ${task}은 이미 실행 중입니다."
          lab_print_task "${task}"
          exit 0
          ;;
        transitional)
          lab_die "Task ${task}의 공식 Lab이 전환 중입니다 (${LAB_COURSE_STATUS_VALUE}). 잠시 후 inspect/reset을 실행하세요."
          ;;
        recoverable)
          lab_die "Task ${task}의 공식 Lab이 Attempted 상태입니다. 'ai267 reset ${task}'으로 lab finish 정리를 재시도하세요."
          ;;
        terminal)
          lab_die "Task ${task} 상태 파일은 남아 있지만 공식 Lab은 종료되어 있습니다. 'ai267 reset ${task}'으로 fixture 정리를 완료하세요."
          ;;
      esac
    fi
    if [[ -n "${CURRENT_TASK}" ]]; then
      lab_die "Task ${CURRENT_TASK}이 실행 중입니다. 먼저 'ai267 finish ${CURRENT_TASK}' 또는 'ai267 reset ${CURRENT_TASK}'을 실행하세요."
    fi

    active_output=
    if ! active_output=$(lab_active_course_labs); then
      lab_die '공식 Lab 상태를 모두 확인하지 못했습니다. 상태가 복구된 뒤 다시 시도하세요.'
    fi
    active_labs=()
    if [[ -n "${active_output}" ]]; then
      mapfile -t active_labs <<< "${active_output}"
    fi
    if (( ${#active_labs[@]} > 0 )); then
      lab_die "공식 Lab '${active_labs[*]}'이 이미 실행 또는 전환 중입니다. 해당 Lab을 finish/reset한 뒤 다시 시작하세요."
    fi

    # Mutation 전에 복구 marker를 먼저 원자적으로 기록한다. setup 전 실패는
    # phase=starting으로 남아 reset에서 cleanup hook을 잘못 호출하지 않는다.
    lab_set_current_task "${task}" starting
    lab_log "공식 AI267 3.3 Lab 시작: ${TASK_LAB}"
    start_rc=0
    (cd "${HOME}" && lab start "${TASK_LAB}") || start_rc=$?
    if (( start_rc != 0 )); then
      if lab_query_course_state "${TASK_LAB}" && [[ "${LAB_COURSE_STATE}" == terminal ]]; then
        lab_clear_current_task
        lab_die "lab start ${TASK_LAB}이 rc=${start_rc}로 실패했고 공식 Lab이 시작되지 않았습니다."
      fi
      lab_die "lab start ${TASK_LAB}이 rc=${start_rc}로 실패했습니다. 복구 상태를 보존했으므로 'ai267 reset ${task}'을 실행하세요."
    fi

    if lab_wait_course_started "${TASK_LAB}"; then
      start_wait_rc=0
    else
      start_wait_rc=$?
      if (( start_wait_rc == 1 )) && [[ "${LAB_COURSE_STATE}" == terminal ]]; then
        lab_clear_current_task
        lab_die "${TASK_LAB}이 Started 상태가 되지 않았습니다. 'lab status ${TASK_LAB}'을 확인하세요."
      fi
      lab_die "${TASK_LAB}의 Started 상태를 확인하지 못했습니다. 복구 상태를 보존했으므로 'ai267 reset ${task}'을 실행하세요."
    fi

    lab_set_current_phase setup
    if ! lab_run_hook "${task}" setup; then
      lab_log "Task ${task} 추가 환경 준비에 실패했습니다. 공식 Lab과 fixture 정리를 시도합니다."
      cleanup_done=false
      if cleanup_requires_running_lab; then
        lab_query_course_state "${TASK_LAB}" \
          || lab_die "공식 Lab 상태를 확인하지 못해 fixture 정리를 시작하지 않았습니다. 'ai267 reset ${task}'을 실행하세요."
        if ! run_cleanup_hook; then
          lab_die "Task ${task} cleanup hook이 실패했습니다. 공식 Lab을 보존했으므로 'ai267 reset ${task}'을 다시 실행하세요."
        fi
        cleanup_done=true
      fi
      if ! finish_course_lab; then
        lab_die "공식 Lab 정리를 확인하지 못했습니다. 복구 상태를 보존했으므로 'ai267 reset ${task}'을 실행하세요."
      fi
      if [[ "${cleanup_done}" != true ]] && ! run_cleanup_hook; then
        lab_die "Task ${task} cleanup hook이 실패했습니다. 상태를 보존했으므로 'ai267 reset ${task}'을 다시 실행하세요."
      fi
      lab_clear_current_task
      lab_die "Task ${task} 추가 환경 준비에 실패하여 확인된 리소스는 정리했습니다."
    fi
    lab_set_current_phase active
    lab_log "Task ${task} 준비 완료: ${TASK_TITLE}"
    lab_print_task "${task}"
    ;;
  finish)
    require_current_task
    case "${CURRENT_PHASE}" in
      active|legacy) ;;
      *)
        lab_die "Task ${task}이 정상 active 상태가 아닙니다 (${CURRENT_PHASE}). 채점 finish 대신 'ai267 reset ${task}'으로 복구하세요."
        ;;
    esac
    if ! "${SCRIPT_DIR}/grade-task.sh" "${task}"; then
      printf '\n[ai267] 채점에 통과하지 못했습니다. 수정할 수 있도록 Lab을 그대로 보존합니다.\n' >&2
      printf '[ai267] 상태 확인: ai267 inspect %s\n' "${task}" >&2
      exit 1
    fi
    lab_set_current_phase finishing
    CURRENT_PHASE=finishing
    cleanup_done=false
    if cleanup_requires_running_lab; then
      lab_query_course_state "${TASK_LAB}" \
        || lab_die "공식 Lab 상태를 확인하지 못해 fixture 정리를 시작하지 않았습니다. 'ai267 reset ${task}'을 실행하세요."
      if ! run_cleanup_hook; then
        lab_die "Task ${task} cleanup hook이 실패했습니다. 공식 Lab을 보존했으므로 'ai267 reset ${task}'을 다시 실행하세요."
      fi
      cleanup_done=true
    fi
    lab_log "채점 통과. 공식 Lab 정리: ${TASK_LAB}"
    if ! finish_course_lab; then
      lab_die "공식 Lab의 종료 상태를 확인하지 못했습니다. 상태를 보존했으므로 'ai267 reset ${task}'을 실행하세요."
    fi
    if [[ "${cleanup_done}" != true ]] && ! run_cleanup_hook; then
      lab_die "Task ${task} cleanup hook이 실패했습니다. 상태를 보존했으므로 'ai267 reset ${task}'을 다시 실행하세요."
    fi
    lab_clear_current_task
    lab_log "Task ${task} 정리 완료. 다음 문제를 시작할 수 있습니다."
    ;;
  reset)
    require_current_task
    cleanup_needed=false
    cleanup_hook_required && cleanup_needed=true
    if [[ "${CURRENT_PHASE}" != starting ]]; then
      lab_set_current_phase resetting
      CURRENT_PHASE=resetting
    fi
    lab_log "Task ${task} 풀이를 버리고 공식 Lab을 정리합니다."

    if [[ "${cleanup_needed}" == true ]] && cleanup_requires_running_lab; then
      lab_query_course_state "${TASK_LAB}" \
        || lab_die "공식 Lab 상태가 불명확하여 fixture 정리를 시작하지 않았습니다. 상태를 보존했으므로 연결을 복구한 뒤 다시 시도하세요."
      if ! run_cleanup_hook; then
        lab_die "Task ${task} cleanup hook이 실패했습니다. 공식 Lab을 보존했으므로 reset을 다시 실행하세요."
      fi
      cleanup_needed=false
    fi

    finish_rc=0
    finish_course_lab || finish_rc=$?
    if (( finish_rc == 2 )); then
      lab_die "공식 Lab 상태가 불명확하여 reset을 중단했습니다. 상태를 보존했으므로 status 연결을 복구한 뒤 다시 시도하세요."
    fi
    if (( finish_rc != 0 )); then
      lab_die "lab finish ${TASK_LAB} 후 terminal 상태를 확인하지 못했습니다. Task 상태를 보존했으므로 'lab finish ${TASK_LAB}' 또는 'ai267 reset ${task}'을 다시 시도하세요."
    fi

    if [[ "${cleanup_needed}" == true ]]; then
      if ! run_cleanup_hook; then
        lab_die "Task ${task} cleanup hook이 실패했습니다. 상태를 보존했으므로 reset을 다시 실행하세요."
      fi
    fi
    lab_clear_current_task
    lab_log "Task ${task} 초기화 완료."
    ;;
esac
