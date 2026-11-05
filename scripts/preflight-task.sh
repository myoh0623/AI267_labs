#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$1
lab_require_login

printf 'Task %s preflight\n' "${task}"
printf '%-32s %s\n' 'OpenShift login' "$(oc whoami)"
printf '%-32s %s\n' 'Namespace' "$(lab_task_namespace "${task}")"

check_api() {
  local group=$1 resource=$2 label=$3
  if lab_api_available "${group}" "${resource}"; then
    printf '%-32s %s\n' "${label}" 'AVAILABLE'
  else
    printf '%-32s %s\n' "${label}" 'NOT INSTALLED'
  fi
}

case "${task}" in
  01)
    check_api datasciencecluster.opendatahub.io datascienceclusters 'DataScienceCluster CRD'
    check_api services.platform.opendatahub.io auths 'OpenShift AI Auth CRD'
    ;;
  02)
    check_api kubeflow.org notebooks 'Kubeflow Notebook CRD'
    check_api infrastructure.opendatahub.io hardwareprofiles 'HardwareProfile CRD'
    check_api build.openshift.io buildconfigs 'OpenShift BuildConfig'
    ;;
  03)
    check_api datasciencepipelinesapplications.opendatahub.io datasciencepipelinesapplications 'DSPA CRD'
    if lab_api_available pipelines.kubeflow.org pipelines; then
      printf '%-32s %s\n' 'KFP v2 Pipeline CRD' 'AVAILABLE'
    else
      check_api argoproj.io workflows 'Argo Workflow CRD'
    fi
    check_api kubeflow.org scheduledworkflows 'KFP ScheduledWorkflow CRD'
    ;;
  04|05) check_api serving.kserve.io inferenceservices 'KServe InferenceService CRD' ;;
  06)
    check_api modelregistry.opendatahub.io modelregistries 'Model Registry CRD'
    registry_state=$(oc get datasciencecluster -o jsonpath='{.items[0].status.components.modelregistry.managementState}' 2>/dev/null || true)
    printf '%-32s %s\n' 'Model Registry component' "${registry_state:-UNKNOWN}"
    ;;
  07) check_api trustyai.opendatahub.io trustyaiservices 'TrustyAIService CRD' ;;
  08) check_api trustyai.opendatahub.io lmevaljobs 'LMEvalJob CRD' ;;
  09) printf '%-32s %s\n' 'AI267 reference app' "${AI267_V33_ROOT:-${AI267_V33_ROOT_DEFAULT}}/labs/chapter-09-genai-patterns/app" ;;
esac

if [[ "${task}" == 05 ]]; then
  lab_require_command python3
  gpu_nodes=$(oc get nodes -o json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sum(1 for n in d["items"] if int(n.get("status",{}).get("allocatable",{}).get("nvidia.com/gpu","0")) > 0))')
  printf '%-32s %s\n' 'Nodes with allocatable GPU' "${gpu_nodes}"
fi

printf '\n참고: NOT INSTALLED 항목은 해당 기능이 설치된 RHOAI 3.3 실습 클러스터에서 실행하세요.\n'

