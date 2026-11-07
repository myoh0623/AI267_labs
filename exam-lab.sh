#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXAM_LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${EXAM_LAB_ROOT}/scripts/lab-common.sh"

usage() {
  cat <<'EOF'
Usage:
  ./exam-lab.sh list
  ./exam-lab.sh validate
  ./exam-lab.sh start   <01-12>
  ./exam-lab.sh inspect <01-12>
  ./exam-lab.sh grade   <01-12> [--json]
  ./exam-lab.sh finish  <01-12>
  ./exam-lab.sh reset   <01-12>
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
  start|finish|reset)
    [[ -n "${2:-}" ]] || { usage; exit 2; }
    task=$(lab_normalize_task "${2}") || { usage; exit 2; }
    exec "${LAB_ROOT}/scripts/course-lab.sh" "${action}" "${task}"
    ;;
  inspect|status)
    [[ -n "${2:-}" ]] || { usage; exit 2; }
    task=$(lab_normalize_task "${2}") || { usage; exit 2; }
    exec "${LAB_ROOT}/scripts/status-task.sh" "${task}"
    ;;
  grade)
    [[ -n "${2:-}" ]] || { usage; exit 2; }
    task=$(lab_normalize_task "${2}") || { usage; exit 2; }
    shift 2
    exec "${LAB_ROOT}/scripts/grade-task.sh" "${task}" "$@"
    ;;
  *)
    usage
    exit 2
    ;;
esac
