#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

usage() {
  cat <<'EOF'
Usage:
  ./exam-lab.sh lab-env list
  ./exam-lab.sh lab-env prepare <01-10|all>
  ./exam-lab.sh lab-env status  <01-10|all>
  ./exam-lab.sh lab-env cleanup <01-10|all> [--yes]

교재 Lab은 별도 ai267-chXX-* namespace에 기준 환경만 준비합니다.
시험 문제, ex267-* namespace, 채점 기준은 변경하지 않습니다.
EOF
}

chapters_for_task() {
  case "$1" in
    01|02) printf '%s\n' chapter-02-workbench ;;
    03) printf '%s\n' chapter-06-pipelines chapter-07-pipeline-operations ;;
    04) printf '%s\n' chapter-03-model-serving chapter-04-model-storage ;;
    07) printf '%s\n' chapter-05-trustyai ;;
    08) printf '%s\n' chapter-08-optimization-evaluation ;;
    09) printf '%s\n' chapter-09-genai-patterns ;;
    05|06|10) return 0 ;;
  esac
}

all_chapters() {
  printf '%s\n' \
    chapter-02-workbench \
    chapter-03-model-serving \
    chapter-04-model-storage \
    chapter-05-trustyai \
    chapter-06-pipelines \
    chapter-07-pipeline-operations \
    chapter-08-optimization-evaluation \
    chapter-09-genai-patterns
}

list_mapping() {
  cat <<'EOF'
01  Chapter 02                 MinIO/S3 연결 기준 환경
02  Chapter 02                 Workbench·PVC·커스텀 이미지 기준 환경
03  Chapters 06, 07            DSPA·KFP v2·비교 실행 기준 환경
04  Chapters 03, 04            KServe V2·ModelCar 기준 환경
05  -                          물리 GPU 필요; 기존 Pending 진단 환경 유지
06  -                          Model Registry가 Removed; 기존 증적 계약 유지
07  Chapter 05                 TrustyAI capture·drift 기준 환경
08  Chapter 08                 CPU 양자화·LMEvalJob 스키마 기준 환경
09  Chapter 09                 mock LLM·RAG·guardrail 기준 환경
10  -                          앞선 과제의 증적을 연결하는 통합 과제
EOF
}

run_chapter() {
  local action=$1 chapter=$2 chapter_dir script
  chapter_dir="${AI267_V33_ROOT_DEFAULT}/labs/${chapter}"
  case "${action}" in
    prepare) script=prepare-demo.sh ;;
    status) script=status-demo.sh ;;
    cleanup) script=cleanup.sh ;;
  esac

  if [[ ! -x "${chapter_dir}/${script}" ]]; then
    if [[ "${chapter}" == chapter-09-genai-patterns ]]; then
      lab_log "Chapter 09 전체 Lab이 없습니다. Task 09 prepare가 vendor 앱을 직접 준비하므로 건너뜁니다."
      return
    fi
    lab_die "교재 Lab 실행 파일을 찾을 수 없습니다: ${chapter_dir}/${script}"
  fi

  lab_log "${chapter}: ${action} (시험 문제/namespace에는 변경 없음)"
  if [[ "${action}" == cleanup ]]; then
    "${chapter_dir}/${script}" --yes
  else
    "${chapter_dir}/${script}"
  fi
}

action=${1:-}
target=${2:-}
case "${action}" in
  list)
    list_mapping
    exit 0
    ;;
  prepare|status|cleanup) ;;
  *) usage; exit 2 ;;
esac

[[ -n "${target}" ]] || { usage; exit 2; }
if [[ "${action}" == cleanup && "${3:-}" != --yes ]]; then
  lab_die "교재 기준 환경을 정리하려면 마지막에 --yes를 지정하세요."
fi

lab_require_login
if [[ "${target}" == all ]]; then
  mapfile -t chapters < <(all_chapters)
else
  task=$(lab_normalize_task "${target}") || { usage; exit 2; }
  mapfile -t chapters < <(chapters_for_task "${task}")
  if (( ${#chapters[@]} == 0 )); then
    lab_log "Task ${task}에는 별도 교재 Lab 기준 환경이 필요하지 않습니다. 기존 시험 환경을 사용하세요."
    exit 0
  fi
fi

for chapter in "${chapters[@]}"; do
  run_chapter "${action}" "${chapter}"
done
