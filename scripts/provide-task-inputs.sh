#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$(lab_normalize_task "${1:-}") || lab_die "Task 번호를 지정하세요: 01-10"
task_dir=$(lab_task_dir "${task}")
namespace=$(lab_task_namespace "${task}")

lab_require_login
oc get namespace "${namespace}" >/dev/null 2>&1 || lab_die "시험 namespace가 없습니다: ${namespace}"

create_file_configmap() {
  local name=$1 source=$2 key=$3
  oc create configmap "${name}" -n "${namespace}" \
    --from-file="${key}=${source}" --dry-run=client -o yaml | oc apply -f - >/dev/null
  oc label configmap "${name}" -n "${namespace}" \
    ex267.practice/input=true ex267.practice/task="${task}" --overwrite >/dev/null
}

case "${task}" in
  01)
    oc create configmap exam-provided-identity -n "${namespace}" \
      --from-literal=rbac_subject=developer1 \
      --from-literal=login_account_provided=false \
      --from-literal=course_login_accounts=admin,developer \
      --from-literal=instruction='developer1은 시험에서 지정한 RBAC subject이며 별도 로그인 계정을 만들지 않는다.' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  02)
    create_file_configmap exam-provided-workbench-inputs \
      "${task_dir}/inputs/create_experiment_runs.py" create_experiment_runs.py
    ;;
  03)
    if ! oc get secret dspa-db -n "${namespace}" >/dev/null 2>&1; then
      lab_require_command openssl
      database_password=$(openssl rand -hex 24)
      oc create secret generic dspa-db -n "${namespace}" \
        --from-literal=password="${database_password}" >/dev/null
      unset database_password
    fi
    create_file_configmap exam-provided-pipeline-source \
      "${task_dir}/inputs/fraud_pipeline.py" fraud_pipeline.py
    oc annotate configmap exam-provided-pipeline-source -n "${namespace}" \
      ex267.practice/data-uri='s3://ex267-task03/data/transactions.csv' \
      ex267.practice/source='adapted-from-RedHatTraining/AI26X-apps' --overwrite >/dev/null
    ;;
  04)
    if ! oc get servingruntime kserve-ovms -n "${namespace}" >/dev/null 2>&1; then
      oc process kserve-ovms -n redhat-ods-applications -o yaml | oc apply -n "${namespace}" -f - >/dev/null
    fi
    oc label servingruntime kserve-ovms -n "${namespace}" \
      ex267.practice/input=true ex267.practice/task="${task}" --overwrite >/dev/null

    # RHOAI 3.3.1 converts connection annotations to model.storage but this
    # cluster does not materialize KServe's storage-config bridge.  Provide the
    # bridge as infrastructure so the candidate still completes fraud-s3 and
    # the InferenceService, while the storage initializer can fetch the model.
    lab_require_command jq
    minio_access=$(oc get secret exam-provided-minio -n "${namespace}" \
      -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 --decode)
    minio_secret=$(oc get secret exam-provided-minio -n "${namespace}" \
      -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 --decode)
    minio_endpoint=$(oc get secret exam-provided-minio -n "${namespace}" \
      -o jsonpath='{.data.AWS_S3_ENDPOINT}' | base64 --decode)
    minio_bucket=$(oc get secret exam-provided-minio -n "${namespace}" \
      -o jsonpath='{.data.AWS_S3_BUCKET}' | base64 --decode)
    storage_entry=$(jq -cn \
      --arg access "${minio_access}" --arg secret "${minio_secret}" \
      --arg endpoint "${minio_endpoint}" --arg bucket "${minio_bucket}" \
      '{type:"s3",access_key_id:$access,secret_access_key:$secret,endpoint_url:$endpoint,bucket:$bucket,region:"us-east-1",verify_ssl:"0"}')
    oc create secret generic storage-config -n "${namespace}" \
      --from-literal=fraud-s3="${storage_entry}" --dry-run=client -o yaml | oc apply -f - >/dev/null
    oc label secret storage-config -n "${namespace}" \
      ex267.practice/input=true ex267.practice/task="${task}" --overwrite >/dev/null
    unset minio_access minio_secret minio_endpoint minio_bucket storage_entry
    ;;
  05)
    gpu_nodes=$(oc get nodes -l nvidia.com/gpu.present=true -o name 2>/dev/null | wc -l | tr -d ' ')
    if [[ "${gpu_nodes}" == 0 ]]; then
      gpu_nodes=$(oc get nodes -o jsonpath='{range .items[*]}{.status.allocatable.nvidia\.com/gpu}{"\n"}{end}' \
        2>/dev/null | awk '$1+0 > 0 {count++} END {print count+0}')
    fi
    oc create configmap exam-provided-hardware -n "${namespace}" \
      --from-literal=gpu_node_count="${gpu_nodes}" \
      --from-literal=full_runtime_possible="$([[ "${gpu_nodes}" -gt 0 ]] && printf true || printf false)" \
      --from-literal=note='GPU가 0이면 Pending·Event·scheduler 진단까지만 수행 가능하다.' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  06)
    registry_name=$(oc get modelregistries.modelregistry.opendatahub.io -A \
      -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    registry_namespace=$(oc get modelregistries.modelregistry.opendatahub.io -A \
      -o jsonpath='{.items[0].metadata.namespace}' 2>/dev/null || true)
    registry_route=$(oc get route -n "${registry_namespace:-rhoai-model-registries}" \
      -l app.kubernetes.io/name=model-registry -o jsonpath='{.items[0].spec.host}' 2>/dev/null || true)
    model_root=${AI267_MODEL_REGISTRY_ASSETS:-${HOME}/course/labs/serving-modelregistry/models}
    [[ -d "${model_root}" ]] || lab_die "교재 Model Registry 모델이 없습니다: ${model_root}"
    oc create configmap exam-provided-registry-inputs -n "${namespace}" \
      --from-literal=registry_name="${registry_name:-NOT_READY}" \
      --from-literal=registry_namespace="${registry_namespace:-rhoai-model-registries}" \
      --from-literal=registry_route="${registry_route:-discover-in-dashboard}" \
      --from-literal=model_v1_path="${model_root}/v1" \
      --from-literal=model_v2_path="${model_root}/v2" \
      --from-literal=oci_registry='registry.lab.example.com:8443' \
      --from-literal=oci_repository='redhattraining/models/fraud-risk' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  07)
    oc apply -f "${task_dir}/resources/exam-inputs.yaml" >/dev/null
    create_file_configmap exam-provided-trustyai-reference \
      "${task_dir}/inputs/iris-reference.json" iris-reference.json
    ;;
  08)
    create_file_configmap exam-provided-completion-api \
      "${task_dir}/inputs/mock_completion_api.py" mock_completion_api.py
    oc apply -f "${task_dir}/resources/exam-inputs.yaml" >/dev/null

    oc create configmap exam-provided-evaluation-inputs -n "${namespace}" \
      --from-literal=baseline_model=synthetic-baseline \
      --from-literal=baseline_base_url='http://synthetic-baseline.ex267-t08-evaluation.svc:8080/v1/completions' \
      --from-literal=optimized_model=synthetic-optimized \
      --from-literal=optimized_base_url='http://synthetic-optimized.ex267-t08-evaluation.svc:8080/v1/completions' \
      --from-literal=approved_tokenizer=gpt2 \
      --from-literal=dataset=openbookqa \
      --from-literal=korean_benchmark='taskRecipe tr_0: synthetic-korean-support-v1' \
      --from-literal=safety_benchmark='taskRecipe tr_1: synthetic-access-safety-v1' \
      --from-literal=offline_cache='s3://ex267-task08/lmeval/' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  09)
    oc create configmap exam-provided-rag-inputs -n "${namespace}" \
      --from-literal=source_id=ai267-chapter09-docs \
      --from-literal=source_revision=synthetic-v1 \
      --from-literal=acl_contract='public:model-serving.md;restricted:rag-security.md' \
      --from-literal=embedding_revision=hash-embedding-v1 \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
  10)
    oc create configmap exam-provided-replay-inputs -n "${namespace}" \
      --from-file=model-current.json="${task_dir}/inputs/model-current.json" \
      --from-file=model-previous.json="${task_dir}/inputs/model-previous.json" \
      --from-file=sample.json="${task_dir}/inputs/sample.json" \
      --from-file=replay.py="${task_dir}/inputs/replay.py" \
      --from-file=environment-lock.txt="${task_dir}/inputs/environment-lock.txt" \
      --from-literal=approved_image='registry.redhat.io/rhoai/odh-workbench-jupyter-minimal-cpu-py312-rhel9@sha256:44c8c2789b1773d6a66d68eac85262ac173989f99ae5bc0ea8c192bd1504d3f2' \
      --from-literal=artifact_prefix='s3://ex267-task10/replay/' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    ;;
esac

while IFS= read -r resource; do
  [[ -n "${resource}" ]] || continue
  oc label "${resource}" -n "${namespace}" \
    ex267.practice/input=true ex267.practice/task="${task}" --overwrite >/dev/null
done < <(oc get configmap -n "${namespace}" -o name 2>/dev/null | grep '^configmap/exam-provided-' || true)

printf '[ai267] Task %s 시험 제공 입력 리소스 준비 완료\n' "${task}"
printf '  Console: Workloads -> ConfigMaps/Secrets -> exam-provided-*\n'
printf '  이 리소스는 데이터·코드·런타임 입력이며 채점 대상 답안은 완성하지 않습니다.\n'
