#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-10"
readonly VENV_DIR=/tmp/ai267-task10-venv
readonly VENV_OWNER_FILE="${VENV_DIR}/.ai267-task-owned"

# 다른 복구를 시작하기 전에 recursive-delete target의 ownership을 검증한다.
if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/venv.task-owned" 2>/dev/null || true)" == true ]] \
  && [[ -e "${VENV_DIR}" || -L "${VENV_DIR}" ]]; then
  if [[ ! -d "${VENV_DIR}" || -L "${VENV_DIR}" \
    || "$(sed -n '1p' "${VENV_OWNER_FILE}" 2>/dev/null || true)" != task-10 ]]; then
    printf 'Task 10 cleanup 거부: %s ownership marker가 없습니다.\n' "${VENV_DIR}" >&2
    exit 1
  fi
fi

for filename in simple_pipeline.py simple_rhoai_pipeline.yaml; do
  target="/tmp/${filename}"
  if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/${filename}.present" 2>/dev/null || true)" == true ]] \
    && [[ -f "${TASK_STATE_ROOT}/${filename}.original" ]]; then
    cp -p -- "${TASK_STATE_ROOT}/${filename}.original" "${target}"
  elif [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/${filename}.present" 2>/dev/null || true)" == false ]]; then
    rm -f -- "${target}"
  fi
done
if [[ "$(sed -n '1p' "${TASK_STATE_ROOT}/venv.task-owned" 2>/dev/null || true)" == true ]]; then
  rm -rf -- "${VENV_DIR}"
fi
rm -f -- "${TASK_STATE_ROOT}"/*.present "${TASK_STATE_ROOT}"/*.original \
  "${TASK_STATE_ROOT}/venv.task-owned"
rmdir "${TASK_STATE_ROOT}" 2>/dev/null || true
