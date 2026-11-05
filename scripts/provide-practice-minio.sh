#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$(lab_normalize_task "${1:-}") || lab_die "Task 번호를 지정하세요: 01, 02, 03, 04, 08, 10"
case "${task}" in
  01) bucket=ex267-task01 ;;
  02) bucket=ex267-task02 ;;
  03) bucket=ex267-task03 ;;
  04) bucket=ex267-task04 ;;
  08) bucket=ex267-task08 ;;
  10) bucket=ex267-task10 ;;
  *) lab_die "Task ${task}에는 MinIO 시험 제공값이 필요하지 않습니다." ;;
esac

lab_require_login
lab_require_command base64
lab_require_command mktemp
lab_require_command s3cmd
[[ -n "${MINIO_ACCESS_KEY:-}" && -n "${MINIO_SECRET_KEY:-}" ]] \
  || lab_die "MinIO 자격 증명이 자동으로 로드되지 않았습니다. 'ai267 start ${task}'를 사용하세요."

namespace=$(lab_task_namespace "${task}")
oc get namespace "${namespace}" >/dev/null 2>&1 \
  || lab_die "시험 namespace가 없습니다: ${namespace}"

route_host=$(oc get route minio-api-minio -n minio \
  -o jsonpath='{.spec.host}' 2>/dev/null || true)
if [[ -z "${route_host}" ]]; then
  route_host=$(oc get route -n minio -o jsonpath='{range .items[*]}{.spec.host}{"\n"}{end}' \
    2>/dev/null | awk '/minio-api/ {print; exit}')
fi
[[ -n "${route_host}" ]] || lab_die "MinIO API Route를 찾을 수 없습니다."
endpoint="https://${route_host}"

s3cfg=$(mktemp)
secret_env=$(mktemp)
cleanup_temp() {
  rm -f -- "${s3cfg}" "${secret_env}"
}
trap cleanup_temp EXIT
chmod 600 "${s3cfg}" "${secret_env}"

cat > "${s3cfg}" <<EOF
[default]
access_key = ${MINIO_ACCESS_KEY}
secret_key = ${MINIO_SECRET_KEY}
host_base = ${route_host}
host_bucket = ${route_host}
use_https = True
check_ssl_certificate = False
check_ssl_hostname = False
EOF

if ! s3cmd -c "${s3cfg}" ls "s3://${bucket}" >/dev/null 2>&1; then
  s3cmd -c "${s3cfg}" mb "s3://${bucket}" >/dev/null
fi

printf '%s=%s\n' \
  AWS_ACCESS_KEY_ID "${MINIO_ACCESS_KEY}" \
  AWS_SECRET_ACCESS_KEY "${MINIO_SECRET_KEY}" \
  AWS_S3_ENDPOINT "${endpoint}" \
  AWS_S3_BUCKET "${bucket}" \
  AWS_DEFAULT_REGION us-east-1 > "${secret_env}"

oc create secret generic exam-provided-minio -n "${namespace}" \
  --from-env-file="${secret_env}" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc label secret exam-provided-minio -n "${namespace}" \
  ex267.practice/input=true ex267.practice/task="${task}" --overwrite >/dev/null
oc annotate secret exam-provided-minio -n "${namespace}" \
  openshift.io/display-name='시험 제공 MinIO 입력값' \
  ex267.practice/description='이 값을 문제의 채점 대상 S3 Secret에 적용하세요.' \
  --overwrite >/dev/null

case "${task}" in
  02)
    input_file="${LAB_ROOT}/tasks/02-workbench/inputs/create_experiment_runs.py"
    s3cmd -c "${s3cfg}" put "${input_file}" \
      "s3://${bucket}/input/create_experiment_runs.py" >/dev/null
    input_sha=$(sha256sum "${input_file}" | awk '{print $1}')
    oc create configmap exam-provided-workbench-data -n "${namespace}" \
      --from-literal=input_uri="s3://${bucket}/input/create_experiment_runs.py" \
      --from-literal=input_sha256="${input_sha}" \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  03)
    input_file="${LAB_ROOT}/tasks/03-pipeline/inputs/transactions.csv"
    s3cmd -c "${s3cfg}" put "${input_file}" \
      "s3://${bucket}/data/transactions.csv" >/dev/null
    support_file="${LAB_ROOT}/tasks/03-pipeline/inputs/support-cases.csv"
    s3cmd -c "${s3cfg}" put "${support_file}" \
      "s3://${bucket}/data/support-cases.csv" >/dev/null
    input_sha=$(sha256sum "${input_file}" | awk '{print $1}')
    support_sha=$(sha256sum "${support_file}" | awk '{print $1}')
    oc create configmap exam-provided-pipeline-data -n "${namespace}" \
      --from-literal=dataset_uri="s3://${bucket}/data/transactions.csv" \
      --from-literal=dataset_sha256="${input_sha}" \
      --from-literal=dataset_revision=synthetic-fraud-v1 \
      --from-literal=elyra_dataset_uri="s3://${bucket}/data/support-cases.csv" \
      --from-literal=elyra_dataset_sha256="${support_sha}" \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  04)
    model_root=${AI267_MODEL_REGISTRY_ASSETS:-${HOME}/course/labs/serving-modelregistry/models}
    current_model=$(find "${model_root}/v2/1" -maxdepth 1 -type f -name '*.onnx' -print -quit 2>/dev/null || true)
    previous_model=$(find "${model_root}/v1/1" -maxdepth 1 -type f -name '*.onnx' -print -quit 2>/dev/null || true)
    [[ -f "${current_model}" && -f "${previous_model}" ]] \
      || lab_die "교재 ONNX v1/v2가 없습니다. 먼저 'lab start serving-modelregistry'로 교재 자산을 받으세요."
    s3cmd -c "${s3cfg}" put "${current_model}" \
      "s3://${bucket}/models/fraud/2/1/model.onnx" >/dev/null
    s3cmd -c "${s3cfg}" put "${previous_model}" \
      "s3://${bucket}/models/fraud/1/1/model.onnx" >/dev/null
    current_sha=$(sha256sum "${current_model}" | awk '{print $1}')
    previous_sha=$(sha256sum "${previous_model}" | awk '{print $1}')
    oc create configmap exam-provided-model-artifacts -n "${namespace}" \
      --from-literal=current_storage_uri="s3://${bucket}/models/fraud/2/" \
      --from-literal=current_model_sha256="${current_sha}" \
      --from-literal=rollback_storage_uri="s3://${bucket}/models/fraud/1/" \
      --from-literal=rollback_model_sha256="${previous_sha}" \
      --from-literal=input_name=keras_tensor \
      --from-literal=input_shape='[1,8]' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  08)
    lab_require_command python3
    cache_root=${AI267_LMEVAL_CACHE:-${HOME}/.cache/ai267-lmeval/rhoai-3.3}
    cache_marker="${cache_root}/hf_home/ex267-cache-ready.json"
    if [[ ! -f "${cache_marker}" ]] || ! grep -q 'materialized-v2' "${cache_marker}"; then
      printf '[ai267] LM-Eval offline cache를 최초 1회 준비합니다.\n'
      if [[ ! -x "${cache_root}/venv/bin/python" ]]; then
        python3 -m venv "${cache_root}/venv"
        "${cache_root}/venv/bin/pip" -q install datasets==3.1.0 transformers==4.48.0
      fi
      HF_HOME="${cache_root}/hf_home" \
        "${cache_root}/venv/bin/python" \
        "${LAB_ROOT}/tasks/08-optimization/inputs/prepare_lmeval_cache.py" >/dev/null
    fi
    s3cmd -c "${s3cfg}" sync "${cache_root}/hf_home/" \
      "s3://${bucket}/lmeval/" >/dev/null
    cache_sha=$(sha256sum "${cache_marker}" | awk '{print $1}')
    oc create configmap exam-provided-lmeval-cache -n "${namespace}" \
      --from-literal=offline_path=lmeval/ \
      --from-literal=cache_manifest_sha256="${cache_sha}" \
      --from-literal=dataset='openbookqa@388097ea7776314e93a529163e0fea805b8a6454' \
      --from-literal=tokenizer=gpt2 \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  10)
    replay_dir="${LAB_ROOT}/tasks/10-evidence/inputs"
    for input_file in "${replay_dir}"/*; do
      s3cmd -c "${s3cfg}" put "${input_file}" \
        "s3://${bucket}/replay/$(basename "${input_file}")" >/dev/null
    done
    ;;
esac

for provided_configmap in exam-provided-workbench-data exam-provided-pipeline-data exam-provided-model-artifacts exam-provided-lmeval-cache; do
  if oc get configmap "${provided_configmap}" -n "${namespace}" >/dev/null 2>&1; then
    oc label configmap "${provided_configmap}" -n "${namespace}" \
      ex267.practice/input=true ex267.practice/task="${task}" --overwrite >/dev/null
  fi
done

printf '\n[ai267] 시험 제공값 준비 완료\n'
printf '  Console: Workloads -> Secrets -> exam-provided-minio\n'
printf '  Namespace: %s\n' "${namespace}"
printf '  Bucket: %s (생성 완료)\n' "${bucket}"
printf '  주의: 채점 대상 Secret과 답안 리소스는 일부러 미완성입니다. 문제 지침대로 직접 완성하세요.\n\n'
