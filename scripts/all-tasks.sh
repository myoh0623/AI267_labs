#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

action=${1:-}
shift || true

case "${action}" in
  preflight|prepare|status|grade|cleanup) ;;
  *) lab_die "Unsupported all-task action: ${action}" ;;
esac

lab_require_login
failures=0

for task in 01 02 03 04 05 06 07 08 09 10; do
  printf '\n========== Task %s · %s ==========\n' "${task}" "${action}"

  args=("${task}")
  if [[ "${action}" == cleanup && "${1:-}" == --yes ]]; then
    args+=(--yes)
  elif [[ "${action}" == grade && "${1:-}" == --json ]]; then
    args+=(--json)
  fi

  if ! "${SCRIPT_DIR}/${action}-task.sh" "${args[@]}"; then
    failures=$((failures + 1))
    printf '[ex267-lab] Task %s %s failed. Continuing.\n' "${task}" "${action}" >&2
  fi
done

if (( failures > 0 )); then
  printf '\n[ex267-lab] %s completed with %d failed task(s).\n' "${action}" "${failures}" >&2
  exit 1
fi

printf '\n[ex267-lab] %s completed for all 10 tasks.\n' "${action}"
