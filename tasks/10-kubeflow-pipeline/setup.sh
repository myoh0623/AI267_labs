#!/usr/bin/env bash
set -Eeuo pipefail

readonly TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly TASK_STATE_ROOT="${AI267_STATE_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/ai267-practice}/task-10"
readonly VENV_DIR=/tmp/ai267-task10-venv
readonly VENV_OWNER_FILE="${VENV_DIR}/.ai267-task-owned"

mkdir -p "${TASK_STATE_ROOT}"
chmod 700 "${TASK_STATE_ROOT}"

if [[ -e "${TASK_STATE_ROOT}/venv.task-owned" \
  || -e "${TASK_STATE_ROOT}/simple_pipeline.py.present" \
  || -e "${TASK_STATE_ROOT}/simple_rhoai_pipeline.yaml.present" ]]; then
  printf 'Task 10 state가 이미 있습니다. 먼저 ai267 finish 10 또는 ai267 reset 10을 실행하세요.\n' >&2
  exit 1
fi

if [[ -e "${VENV_DIR}" ]]; then
  printf '%s가 이미 존재합니다. 기존 가상환경을 확인한 뒤 다시 시작하세요.\n' "${VENV_DIR}" >&2
  exit 1
fi

printf 'true\n' > "${TASK_STATE_ROOT}/venv.task-owned"
chmod 600 "${TASK_STATE_ROOT}/venv.task-owned"
for filename in simple_pipeline.py simple_rhoai_pipeline.yaml; do
  target="/tmp/${filename}"
  if [[ -e "${target}" ]]; then
    printf 'true\n' > "${TASK_STATE_ROOT}/${filename}.present"
    cp -p -- "${target}" "${TASK_STATE_ROOT}/${filename}.original"
  else
    printf 'false\n' > "${TASK_STATE_ROOT}/${filename}.present"
  fi
  chmod 600 "${TASK_STATE_ROOT}/${filename}.present"
done
cp -- "${TASK_DIR}/inputs/simple_pipeline.py" /tmp/simple_pipeline.py

# uv refuses an existing directory by default. Reserving the exact path with a
# sentinel and using --allow-existing lets cleanup prove ownership later while
# the learner still creates the actual virtual environment.
mkdir -- "${VENV_DIR}"
printf 'task-10\n' > "${VENV_OWNER_FILE}"
chmod 600 "${VENV_OWNER_FILE}"
