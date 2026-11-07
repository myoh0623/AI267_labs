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
      --from-literal=allowed_group=devops-wala \
      --from-literal=allowed_group_members=developer,rajan,punit \
      --from-literal=admin_group=rhoai-exam-admins \
      --from-literal=admin_group_members=raja,andrew \
      --from-literal=instruction='지정된 이름은 RBAC/Auth subject다. OAuth 암호 파일을 수정하거나 별도 로그인 계정을 만들 필요가 없다.' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    lab_require_command jq
    auth_json=$(oc get auth.services.platform.opendatahub.io auth -o json 2>/dev/null \
      | jq -c '{apiVersion,kind,metadata:{name:.metadata.name},spec}' || printf '{}')
    oc create configmap exam-provided-auth-backup -n "${namespace}" \
      --from-literal=auth.json="${auth_json}" \
      --from-literal=restore_note='Task 01 cleanup이 기존 Auth spec을 복원한다.' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    unset auth_json
    ;;
  02)
    create_file_configmap exam-provided-workbench-inputs \
      "${task_dir}/inputs/create_experiment_runs.py" create_experiment_runs.py
    oc create configmap exam-provided-custom-image-source -n "${namespace}" \
      --from-file=Containerfile="${task_dir}/inputs/custom-image/Containerfile" \
      --from-file=requirements.txt="${task_dir}/inputs/custom-image/requirements.txt" \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    oc create configmap exam-provided-workbench-compatibility -n "${namespace}" \
      --from-literal=legacy_size_selector='RHOAI 3.0부터 HardwareProfile로 대체됨' \
      --from-literal=required_profiles='MediumSmall:1-2CPU/16Gi, My-medium:1-2CPU/1-2Gi' \
      --from-literal=git_repository='https://github.com/RedHatTraining/AI26X-apps' \
      --from-literal=git_branch=RHOAI3.3 \
      --from-literal=existing_workbench=git-experiments \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    lab_require_command jq
    culler_existed=false
    culler_json='{}'
    if oc get configmap notebook-controller-culler-config -n redhat-ods-applications >/dev/null 2>&1; then
      culler_existed=true
      culler_json=$(oc get configmap notebook-controller-culler-config -n redhat-ods-applications -o json \
        | jq -c '{apiVersion,kind,metadata:{name:.metadata.name,namespace:.metadata.namespace},data}')
    fi
    oc create configmap exam-provided-culler-backup -n "${namespace}" \
      --from-literal=existed="${culler_existed}" \
      --from-literal=culler.json="${culler_json}" \
      --from-literal=restore_note='Task 02 cleanup이 기존 notebook culler 설정을 복원한다.' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    unset culler_existed culler_json
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
    oc create configmap exam-provided-elyra-source -n "${namespace}" \
      --from-file=data_ingestion.py="${task_dir}/inputs/elyra/data_ingestion.py" \
      --from-file=data_preprocessing.py="${task_dir}/inputs/elyra/data_preprocessing.py" \
      --from-file=data_training_and_forecasting.py="${task_dir}/inputs/elyra/data_training_and_forecasting.py" \
      --from-file=issues_prediction.pipeline="${task_dir}/inputs/elyra/issues_prediction.pipeline" \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    oc annotate configmap exam-provided-pipeline-source -n "${namespace}" \
      ex267.practice/data-uri='s3://ex267-task03/data/transactions.csv' \
      ex267.practice/source='adapted-from-RedHatTraining/AI26X-apps' --overwrite >/dev/null
    oc create configmap exam-provided-elyra-contract -n "${namespace}" \
      --from-literal=pipeline_file=issues_prediction.pipeline \
      --from-literal=workbench=pipelines-elyra-wb \
      --from-literal=pvc_size=10Gi \
      --from-literal=runtime_image='quay.io/redhattraining/forecast-pipeline-runtime:1.0' \
      --from-literal=connection=aws-connection-fraud-s3 \
      --from-literal=outputs='data.csv,clean-data.csv,forecast-data.csv' \
      --from-literal=schedule_seconds=300 \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
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
    multimodel_api=false
    if oc api-resources --api-group=serving.kserve.io -o name 2>/dev/null \
      | grep -q '^inferenceservices'; then
      if oc get deployments -A -l control-plane=modelmesh-controller -o name 2>/dev/null | grep -q .; then
        multimodel_api=true
      fi
    fi
    oc create configmap exam-provided-serving-compatibility -n "${namespace}" \
      --from-literal=source_version=RHOAI2.13 \
      --from-literal=current_version=RHOAI3.3 \
      --from-literal=modelmesh_available="${multimodel_api}" \
      --from-literal=legacy_mode='ModelMesh multi-model' \
      --from-literal=current_mode='KServe RawDeployment with external route and optional token authentication' \
      --from-literal=custom_runtime_source=kserve-ovms \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
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
    lab_require_command openssl
    lab_require_command htpasswd
    lab_require_command curl
    if ! oc get secret exam-provided-oci-credentials -n "${namespace}" >/dev/null 2>&1 \
      || ! oc get secret exam-provided-oci-auth -n "${namespace}" >/dev/null 2>&1; then
      oc delete secret exam-provided-oci-credentials exam-provided-oci-auth exam-provided-oci-pull \
        -n "${namespace}" --ignore-not-found >/dev/null
      registry_username=ai267
      registry_password=$(openssl rand -hex 18)
      registry_htpasswd=$(htpasswd -Bbn "${registry_username}" "${registry_password}")
      oc create secret generic exam-provided-oci-credentials -n "${namespace}" \
        --from-literal=username="${registry_username}" \
        --from-literal=password="${registry_password}" >/dev/null
      oc create secret generic exam-provided-oci-auth -n "${namespace}" \
        --from-literal=htpasswd="${registry_htpasswd}" >/dev/null
      oc label secret exam-provided-oci-credentials exam-provided-oci-auth -n "${namespace}" \
        ex267.practice/input=true ex267.practice/task=06 --overwrite >/dev/null
      unset registry_username registry_password registry_htpasswd
    fi
    oc apply -f "${task_dir}/resources/practice-oci-registry.yaml" >/dev/null
    oc rollout status deployment/practice-oci-registry -n "${namespace}" --timeout=180s >/dev/null
    practice_registry=$(oc get route practice-oci-registry -n "${namespace}" \
      -o jsonpath='{.spec.host}')
    [[ -n "${practice_registry}" ]] || lab_die 'Task 06 전용 OCI Registry Route를 찾지 못했습니다.'

    registry_username=$(oc get secret exam-provided-oci-credentials -n "${namespace}" \
      -o go-template='{{index .data "username" | base64decode}}')
    registry_password=$(oc get secret exam-provided-oci-credentials -n "${namespace}" \
      -o go-template='{{index .data "password" | base64decode}}')
    oc create secret docker-registry exam-provided-oci-pull -n "${namespace}" \
      --docker-server="${practice_registry}" \
      --docker-username="${registry_username}" \
      --docker-password="${registry_password}" \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    oc label secret exam-provided-oci-pull -n "${namespace}" \
      ex267.practice/input=true ex267.practice/task=06 --overwrite >/dev/null
    oc secrets link default exam-provided-oci-pull -n "${namespace}" --for=pull
    registry_ready=false
    for _ in $(seq 1 30); do
      if curl --fail --silent --show-error --insecure \
        --user "${registry_username}:${registry_password}" \
        "https://${practice_registry}/v2/" >/dev/null 2>&1; then
        registry_ready=true
        break
      fi
      sleep 2
    done
    [[ "${registry_ready}" == true ]] \
      || lab_die 'Task 06 전용 OCI Registry 인증 smoke test가 실패했습니다.'
    unset registry_username registry_password registry_ready

    registry_name=$(oc get modelregistries.modelregistry.opendatahub.io -A \
      -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    registry_namespace=$(oc get modelregistries.modelregistry.opendatahub.io -A \
      -o jsonpath='{.items[0].metadata.namespace}' 2>/dev/null || true)
    registry_namespace=${registry_namespace:-rhoai-model-registries}
    registry_service=$(oc get service -n "${registry_namespace}" \
      -l component=model-registry -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    registry_service=${registry_service:-${registry_name}}
    [[ -n "${registry_name}" && -n "${registry_service}" ]] \
      || lab_die '사용 가능한 Model Registry instance/service를 찾지 못했습니다.'
    registry_port=$(oc get service "${registry_service}" -n "${registry_namespace}" \
      -o jsonpath='{.spec.ports[?(@.port==8080)].name}' 2>/dev/null || true)
    registry_port=${registry_port:-http-api}
    registry_rest_api=/api/model_registry/v1alpha3
    registry_proxy_prefix="/api/v1/namespaces/${registry_namespace}/services/${registry_service}:${registry_port}/proxy"
    model_root=${AI267_MODEL_REGISTRY_ASSETS:-${HOME}/course/labs/serving-modelregistry/models}
    [[ -d "${model_root}" ]] || lab_die "교재 Model Registry 모델이 없습니다: ${model_root}"
    oc create configmap exam-provided-registry-inputs -n "${namespace}" \
      --from-literal=registry_name="${registry_name}" \
      --from-literal=registry_namespace="${registry_namespace}" \
      --from-literal=registry_service="${registry_service}" \
      --from-literal=registry_service_port="${registry_port}" \
      --from-literal=registry_service_url="http://${registry_service}.${registry_namespace}.svc:8080" \
      --from-literal=registry_rest_api="${registry_rest_api}" \
      --from-literal=registry_proxy_prefix="${registry_proxy_prefix}" \
      --from-literal=model_v1_path="${model_root}/v1" \
      --from-literal=model_v2_path="${model_root}/v2" \
      --from-literal=oci_registry="${practice_registry}" \
      --from-literal=oci_repository='redhattraining/models/fraud-risk' \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    unset practice_registry
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
      --from-literal=authorized_identity=security-reviewer \
      --from-literal=unauthorized_identity=external-user \
      --dry-run=client -o yaml | oc apply -f - >/dev/null
    create_file_configmap exam-provided-rag-verifier \
      "${task_dir}/inputs/verify_rag.py" verify_rag.py
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
