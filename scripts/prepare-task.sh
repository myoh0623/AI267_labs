#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$1
task_dir=$(lab_task_dir "${task}")
namespace=$(lab_task_namespace "${task}")
seed_file="${task_dir}/resources/seed.yaml"

lab_require_login
[[ -f "${seed_file}" ]] || lab_die "Seed manifest not found: ${seed_file}"

if oc get namespace "${namespace}" >/dev/null 2>&1 && ! lab_verify_managed_namespace "${task}" "${namespace}"; then
  lab_die "Namespace ${namespace} exists but is not owned by EX267 task ${task}. Refusing to modify it."
fi

lab_log "Preparing task ${task} in namespace ${namespace}"
oc apply -f "${seed_file}"

if [[ "${task}" == 09 ]]; then
  ref_root=${AI267_V33_ROOT:-${AI267_V33_ROOT_DEFAULT}}
  app_dir="${ref_root}/labs/chapter-09-genai-patterns/app"
  docs_dir="${ref_root}/labs/chapter-09-genai-patterns/docs"
  if [[ ! -f "${app_dir}/mock_llm.py" ]]; then
    app_dir="${LAB_ROOT}/vendor/chapter-09-genai-patterns/app"
    docs_dir="${LAB_ROOT}/vendor/chapter-09-genai-patterns/docs"
  fi
  [[ -f "${app_dir}/mock_llm.py" && -f "${app_dir}/tool_service.py" && -f "${app_dir}/genai_app.py" ]] \
    || lab_die "AI267 v3.3 Chapter 09 reference app was not found under ${app_dir}"

  oc create configmap mock-llm-code -n "${namespace}" \
    --from-file=mock_llm.py="${app_dir}/mock_llm.py" --dry-run=client -o yaml | oc apply -f -
  oc create configmap tool-service-code -n "${namespace}" \
    --from-file=tool_service.py="${app_dir}/tool_service.py" --dry-run=client -o yaml | oc apply -f -
  oc create configmap genai-app-code -n "${namespace}" \
    --from-file=genai_app.py="${app_dir}/genai_app.py" --dry-run=client -o yaml | oc apply -f -
  oc create configmap rag-documents -n "${namespace}" \
    --from-file="${docs_dir}" --dry-run=client -o yaml | oc apply -f -

  if ! oc get secret tool-identity -n "${namespace}" >/dev/null 2>&1; then
    lab_require_command openssl
    tool_token=$(openssl rand -hex 24)
    oc create secret generic tool-identity -n "${namespace}" --from-literal=token="${tool_token}" >/dev/null
    unset tool_token
  fi

  oc apply -f "${task_dir}/resources/application.yaml"
fi

lab_log "Task ${task} seed is ready. Read ${task_dir}/README.md, solve in the Console, then run:"
printf '  %s/exam-lab.sh grade %s\n' "${LAB_ROOT}" "${task}"

