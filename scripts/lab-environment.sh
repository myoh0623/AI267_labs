#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

usage() {
  cat <<'EOF'
Usage:
  ./exam-lab.sh lab-env list
  ./exam-lab.sh lab-env switch  <01-10>
  ./exam-lab.sh lab-env prepare <01-10>
  ./exam-lab.sh lab-env status  <01-10|all>
  ./exam-lab.sh lab-env cleanup <01-10|all> [--yes]

교재 Lab은 별도 ai267-chXX-* namespace에 기준 환경만 준비합니다.
시험 문제, ex267-* namespace, 채점 기준은 변경하지 않습니다.
EOF
}

chapters_for_task() {
  case "$1" in
    01|02) printf '%s\n' chapter-02-workbench ;;
    03) printf '%s\n' chapter-06-pipelines ;;
    04) printf '%s\n' chapter-04-model-storage ;;
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
03  Chapter 06                 DSPA·KFP v2 기준 환경
04  Chapter 04                 KServe V2·ModelCar 기준 환경
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

chapter_namespace() {
  case "$1" in
    chapter-02-workbench) printf '%s\n' ai267-ch02-workbench ;;
    chapter-03-model-serving) printf '%s\n' ai267-ch03-serving ;;
    chapter-04-model-storage) printf '%s\n' ai267-ch04-storage ;;
    chapter-05-trustyai) printf '%s\n' ai267-ch05-trustyai ;;
    chapter-06-pipelines) printf '%s\n' ai267-ch06-pipelines ;;
    chapter-07-pipeline-operations) printf '%s\n' ai267-ch07-pipeline-ops ;;
    chapter-08-optimization-evaluation) printf '%s\n' ai267-ch08-evaluation ;;
    chapter-09-genai-patterns) printf '%s\n' ai267-ch09-genai ;;
  esac
}

cleanup_active_chapters() {
  local chapter namespace chapter_dir
  while IFS= read -r chapter; do
    namespace=$(chapter_namespace "${chapter}")
    oc get namespace "${namespace}" >/dev/null 2>&1 || continue
    chapter_dir="${AI267_V33_ROOT_DEFAULT}/labs/${chapter}"
    [[ -x "${chapter_dir}/cleanup.sh" ]] || continue
    lab_log "활성 교재 Lab 정리: ${chapter}"
    case "${chapter}" in
      chapter-02-workbench) "${chapter_dir}/cleanup.sh" --yes --keep-catalog ;;
      chapter-06-pipelines|chapter-07-pipeline-operations)
        "${chapter_dir}/cleanup.sh" --yes --keep-bucket
        ;;
      *) "${chapter_dir}/cleanup.sh" --yes ;;
    esac
  done < <(all_chapters)
}

action=${1:-}
target=${2:-}
case "${action}" in
  list)
    list_mapping
    exit 0
    ;;
  switch|prepare|status|cleanup) ;;
  *) usage; exit 2 ;;
esac

[[ -n "${target}" ]] || { usage; exit 2; }
if [[ "${action}" == prepare && "${target}" == all ]]; then
  lab_die "교재 Lab은 동시에 실행하지 않습니다. 'lab-env switch <task>'로 한 문제씩 전환하세요."
fi
if [[ "${action}" == switch && "${target}" == all ]]; then
  lab_die "switch에는 하나의 문제 번호만 지정하세요."
fi
if [[ "${action}" == cleanup && "${3:-}" != --yes ]]; then
  lab_die "교재 기준 환경을 정리하려면 마지막에 --yes를 지정하세요."
fi

lab_require_login
if [[ "${action}" == switch ]]; then
  task=$(lab_normalize_task "${target}") || { usage; exit 2; }
  mapfile -t chapters < <(chapters_for_task "${task}")
  cleanup_active_chapters
  if (( ${#chapters[@]} == 0 )); then
    lab_log "Task ${task}에는 별도 교재 Lab 기준 환경이 필요하지 않습니다."
    exit 0
  fi
  for chapter in "${chapters[@]}"; do
    run_chapter prepare "${chapter}"
  done
  exit 0
fi

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

if [[ "${action}" == prepare ]]; then
  desired_namespace=$(chapter_namespace "${chapters[0]}")
  while IFS= read -r candidate; do
    candidate_namespace=$(chapter_namespace "${candidate}")
    if [[ "${candidate_namespace}" != "${desired_namespace}" ]] \
      && oc get namespace "${candidate_namespace}" >/dev/null 2>&1; then
      lab_die "${candidate_namespace} Lab이 이미 실행 중입니다. 'lab-env switch ${task}'를 사용하세요."
    fi
  done < <(all_chapters)
fi

for chapter in "${chapters[@]}"; do
  run_chapter "${action}" "${chapter}"
done
