#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXAM_LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${EXAM_LAB_ROOT}/scripts/lab-common.sh"

usage() {
  cat <<'EOF'
Usage:
  ./exam-lab.sh list
  ./exam-lab.sh validate
  ./exam-lab.sh preflight-all
  ./exam-lab.sh prepare-all
  ./exam-lab.sh status-all
  ./exam-lab.sh grade-all [--json]
  ./exam-lab.sh cleanup-all [--yes]
  ./exam-lab.sh preflight <01-10>
  ./exam-lab.sh prepare   <01-10>
  ./exam-lab.sh status    <01-10>
  ./exam-lab.sh grade     <01-10> [--json]
  ./exam-lab.sh cleanup   <01-10> [--yes]
EOF
}

action=${1:-}
case "${action}" in
  list)
    lab_list_tasks
    ;;
  validate)
    exec "${LAB_ROOT}/scripts/validate-local.sh"
    ;;
  preflight-all|prepare-all|status-all|grade-all|cleanup-all)
    exec "${LAB_ROOT}/scripts/all-tasks.sh" "${action%-all}" "${@:2}"
    ;;
  preflight|prepare|status|grade|cleanup)
    task=${2:-}
    [[ -n "${task}" ]] || { usage; exit 2; }
    task=$(lab_normalize_task "${task}") || { usage; exit 2; }
    shift 2
    exec "${LAB_ROOT}/scripts/${action}-task.sh" "${task}" "$@"
    ;;
  *)
    usage
    exit 2
    ;;
esac
