#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

read_minio_secret_value() {
  local key encoded
  for key in "$@"; do
    encoded=$(oc get secret minio-secret -n minio \
      -o "jsonpath={.data.${key}}" 2>/dev/null || true)
    if [[ -n "${encoded}" ]]; then
      printf '%s' "${encoded}" | base64 --decode
      return 0
    fi
  done
  return 1
}

load_course_minio_credentials() {
  local access_key secret_key
  if [[ -n "${MINIO_ACCESS_KEY:-}" && -n "${MINIO_SECRET_KEY:-}" ]]; then
    return 0
  fi
  oc get secret minio-secret -n minio >/dev/null 2>&1 || return 0
  access_key=$(read_minio_secret_value minio_root_user MINIO_ROOT_USER accesskey AWS_ACCESS_KEY_ID) || true
  secret_key=$(read_minio_secret_value minio_root_password MINIO_ROOT_PASSWORD secretkey AWS_SECRET_ACCESS_KEY) || true
  [[ -n "${access_key}" && -n "${secret_key}" ]] || return 0
  export MINIO_ACCESS_KEY=${access_key}
  export MINIO_SECRET_KEY=${secret_key}
  unset access_key secret_key
}

usage() {
  cat <<'EOF'
Usage:
  ./exam-lab.sh lab-env list
  ./exam-lab.sh lab-env switch  <01-10>
  ./exam-lab.sh lab-env prepare <01-10>
  ./exam-lab.sh lab-env status  <01-10|all>
  ./exam-lab.sh lab-env cleanup <01-10|all> [--yes]

교재 Lab은 별도 ai267-chXX-* namespace에 기준 환경만 준비합니다.
기존 10개 문제는 유지하며 번호형 실습 행동은 해당 Task의 추가 채점 항목으로 검증합니다.
EOF
}

chapters_for_task() {
  case "$1" in
    01) printf '%s\n' chapter-01-projects ;;
    02) printf '%s\n' chapter-02-workbench ;;
    03) printf '%s\n' chapter-06-pipelines ;;
    04) printf '%s\n' chapter-04-model-storage ;;
    07) printf '%s\n' chapter-05-trustyai ;;
    08) printf '%s\n' chapter-08-optimization-evaluation ;;
    09) printf '%s\n' chapter-09-genai-patterns ;;
    05|06|10) return 0 ;;
  esac
}

course_lab_for_task() {
  case "$1" in
    06) printf '%s\n' serving-modelregistry ;;
  esac
}

course_lab_is_started() {
  local course_lab=$1
  command -v lab >/dev/null 2>&1 || return 1
  lab status "${course_lab}" 2>/dev/null | grep -q 'Status: Started'
}

cleanup_active_course_labs() {
  local keep=${1:-} course_lab
  for course_lab in serving-modelregistry; do
    [[ "${course_lab}" == "${keep}" ]] && continue
    if course_lab_is_started "${course_lab}"; then
      lab_log "활성 교재 Lab 정리: ${course_lab}"
      (cd "${HOME}" && lab finish "${course_lab}")
    fi
  done
}

all_chapters() {
  printf '%s\n' \
    chapter-01-projects \
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
01  Chapter 01                 플랫폼·프로젝트·RBAC 기준 환경
02  Chapter 02                 Workbench·PVC·커스텀 이미지·Git 기준 환경
03  Chapter 06                 DSPA·KFP v2·Elyra·예약 실행 기준 환경
04  Chapter 04                 KServe V2·custom runtime·인증 기준 환경
05  -                          물리 GPU 필요; 기존 Pending 진단 환경 유지
06  serving-modelregistry      Model Registry·MariaDB·ONNX v1/v2·교실 OCI registry
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
  load_course_minio_credentials
  if [[ "${chapter}" == chapter-02-workbench && "${action}" == prepare ]] \
    && ! oc whoami -t >/dev/null 2>&1; then
    lab_log "인증서 kubeconfig 감지: Workbench OAuth URL 검사 대신 Pod Ready를 검증합니다."
    bash "${LAB_ROOT}/scripts/prepare-chapter02-cert-auth.sh" "${chapter_dir}"
    return
  fi
  if [[ "${action}" == cleanup ]]; then
    "${chapter_dir}/${script}" --yes
  else
    "${chapter_dir}/${script}"
  fi
}

chapter_namespace() {
  case "$1" in
    chapter-01-projects) printf '%s\n' ai267-ch01-projects ;;
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
  course_lab=$(course_lab_for_task "${task}" || true)
  cleanup_active_chapters
  cleanup_active_course_labs "${course_lab}"
  if [[ -n "${course_lab}" ]] && ! course_lab_is_started "${course_lab}"; then
    command -v lab >/dev/null 2>&1 \
      || lab_die "교재 Lab 명령을 찾을 수 없습니다: lab start ${course_lab}"
    lab_log "${course_lab}: start (시험 문제/namespace에는 변경 없음)"
    (cd "${HOME}" && lab start "${course_lab}")
  fi
  if (( ${#chapters[@]} == 0 )) && [[ -z "${course_lab}" ]]; then
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
  course_lab=$(course_lab_for_task "${task}" || true)
  if [[ -n "${course_lab}" ]]; then
    case "${action}" in
      status) (cd "${HOME}" && lab status "${course_lab}") ;;
      cleanup)
        if course_lab_is_started "${course_lab}"; then
          (cd "${HOME}" && lab finish "${course_lab}")
        else
          lab_log "${course_lab} 교재 Lab은 실행 중이 아닙니다."
        fi
        ;;
      prepare)
        if ! course_lab_is_started "${course_lab}"; then
          (cd "${HOME}" && lab start "${course_lab}")
        fi
        ;;
    esac
    exit 0
  fi
  if (( ${#chapters[@]} == 0 )); then
    lab_log "Task ${task}에는 별도 교재 Lab 기준 환경이 필요하지 않습니다. 기존 시험 환경을 사용하세요."
    exit 0
  fi
fi

if [[ "${target}" == all && "${action}" == cleanup ]]; then
  cleanup_active_course_labs
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
