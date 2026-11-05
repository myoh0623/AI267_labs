#!/usr/bin/env bash

set -Eeuo pipefail

readonly LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
lab_find_ai267_root() {
  local candidate
  if [[ -n "${AI267_V33_ROOT:-}" ]]; then
    printf '%s\n' "${AI267_V33_ROOT}"
    return
  fi

  for candidate in \
    "${HOME}/ai267-v3.3" \
    "${HOME}/course" \
    "/home/omy-agent/redhat/openshift/ai/ai267/v3.3"; do
    if [[ -d "${candidate}/labs" ]]; then
      printf '%s\n' "${candidate}"
      return
    fi
  done

  printf '%s\n' "${HOME}/ai267-v3.3"
}

readonly AI267_V33_ROOT_DEFAULT=$(lab_find_ai267_root)

lab_log() {
  printf '[ex267-lab] %s\n' "$*"
}

lab_die() {
  printf '[ex267-lab] ERROR: %s\n' "$*" >&2
  exit 1
}

lab_require_command() {
  command -v "$1" >/dev/null 2>&1 || lab_die "Required command not found: $1"
}

lab_require_login() {
  lab_require_command oc
  oc whoami >/dev/null 2>&1 || lab_die "OpenShift에 먼저 로그인하세요: oc login ..."
}

lab_normalize_task() {
  case "$1" in
    1|01) printf '01\n' ;;
    2|02) printf '02\n' ;;
    3|03) printf '03\n' ;;
    4|04) printf '04\n' ;;
    5|05) printf '05\n' ;;
    6|06) printf '06\n' ;;
    7|07) printf '07\n' ;;
    8|08) printf '08\n' ;;
    9|09) printf '09\n' ;;
    10) printf '10\n' ;;
    *) return 1 ;;
  esac
}

lab_task_slug() {
  case "$1" in
    01) printf '01-foundation\n' ;;
    02) printf '02-workbench\n' ;;
    03) printf '03-pipeline\n' ;;
    04) printf '04-predictive-serving\n' ;;
    05) printf '05-vllm-gpu\n' ;;
    06) printf '06-model-registry\n' ;;
    07) printf '07-monitoring\n' ;;
    08) printf '08-optimization\n' ;;
    09) printf '09-rag\n' ;;
    10) printf '10-evidence\n' ;;
  esac
}

lab_task_namespace() {
  case "$1" in
    01) printf 'ex267-fraud\n' ;;
    02) printf 'ex267-t02-workbench\n' ;;
    03) printf 'ex267-t03-pipeline\n' ;;
    04) printf 'ex267-t04-serving\n' ;;
    05) printf 'ex267-t05-vllm\n' ;;
    06) printf 'ex267-t06-registry\n' ;;
    07) printf 'ex267-t07-monitoring\n' ;;
    08) printf 'ex267-t08-evaluation\n' ;;
    09) printf 'ex267-t09-rag\n' ;;
    10) printf 'ex267-t10-evidence\n' ;;
  esac
}

lab_task_points() {
  case "$1" in
    01|08|10) printf '24\n' ;;
    02|05|06|07) printf '30\n' ;;
    03|04|09) printf '36\n' ;;
  esac
}

lab_task_dir() {
  printf '%s/tasks/%s\n' "${LAB_ROOT}" "$(lab_task_slug "$1")"
}

lab_list_tasks() {
  cat <<'EOF'
01  프로젝트·RBAC·S3 연결               24점
02  Workbench·PVC·실험 증적             30점
03  KFP v2 Pipeline·실험 비교           36점
04  OpenVINO KServe 모델 서빙            36점
05  vLLM·GPU 배치 진단                  30점
06  Model Registry·계보                 30점
07  TrustyAI·플랫폼 모니터링             30점
08  LLM 최적화·LMEval                   24점
09  Guardrailed RAG                     36점
10  재현·증적·롤백                      24점
EOF
}

lab_api_available() {
  local group=$1 resource=$2
  oc api-resources --api-group="${group}" -o name 2>/dev/null \
    | grep -Eq "^(${resource}|${resource}\.${group})$"
}

lab_verify_managed_namespace() {
  local task=$1 namespace=$2 managed task_label
  managed=$(oc get namespace "${namespace}" -o jsonpath='{.metadata.labels.ex267\.practice/managed}' 2>/dev/null || true)
  task_label=$(oc get namespace "${namespace}" -o jsonpath='{.metadata.labels.ex267\.practice/task}' 2>/dev/null || true)
  [[ "${managed}" == true && "${task_label}" == "${task}" ]]
}

