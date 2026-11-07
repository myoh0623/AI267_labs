#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$1
lab_require_login

printf 'Task %s 환경 사전 점검 (무점수)\n' "${task}"
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
    lab_require_command python3
    rhoai_csv=$(oc get clusterserviceversion -A -o json 2>/dev/null \
      | python3 -c 'import json,sys; items=[i for i in json.load(sys.stdin).get("items",[]) if "openshift ai" in i.get("spec",{}).get("displayName","").lower() or "rhods-operator" in i.get("metadata",{}).get("name","").lower()]; good=[i["metadata"]["name"] for i in items if i.get("status",{}).get("phase")=="Succeeded"]; print("Succeeded: "+",".join(good) if good else (", ".join(i.get("metadata",{}).get("name","")+"="+i.get("status",{}).get("phase","UNKNOWN") for i in items) or "NOT FOUND"))' \
      2>/dev/null || printf 'UNKNOWN')
    dsc_ready=$(oc get datasciencecluster -o json 2>/dev/null \
      | python3 -c 'import json,sys; items=json.load(sys.stdin).get("items",[]); good=[i.get("metadata",{}).get("name","") for i in items if any(c.get("type")=="Ready" and str(c.get("status","")).lower()=="true" for c in i.get("status",{}).get("conditions",[]))]; print("Ready: "+",".join(good) if good else "NOT READY")' \
      2>/dev/null || printf 'UNKNOWN')
    dashboard_replicas=$(oc get deployment rhods-dashboard -n redhat-ods-applications \
      -o jsonpath='{.status.availableReplicas}' 2>/dev/null || true)
    printf '%-32s %s\n' 'Red Hat OpenShift AI CSV' "${rhoai_csv}"
    printf '%-32s %s\n' 'DataScienceCluster state' "${dsc_ready}"
    if [[ "${dashboard_replicas:-0}" =~ ^[0-9]+$ ]] && (( dashboard_replicas > 0 )); then
      printf '%-32s %s\n' 'RHOAI Dashboard deployment' "READY (${dashboard_replicas} replicas)"
    else
      printf '%-32s %s\n' 'RHOAI Dashboard deployment' 'NOT READY'
    fi
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
    lab_require_command python3
    if [[ -n "$(oc get modelregistries.modelregistry.opendatahub.io -A -o name 2>/dev/null || true)" ]]; then
      oc wait --for=condition=Available modelregistries.modelregistry.opendatahub.io \
        --all --all-namespaces --timeout=180s >/dev/null 2>&1 || true
    fi
    registry_components=$(oc get datasciencecluster -o json 2>/dev/null \
      | python3 -c 'import json,sys; items=json.load(sys.stdin).get("items",[]); values=[i.get("metadata",{}).get("name","")+"="+i.get("status",{}).get("components",{}).get("modelregistry",{}).get("managementState","UNKNOWN") for i in items]; print(", ".join(values) or "UNKNOWN")' \
      2>/dev/null || printf 'UNKNOWN')
    registry_instances=$(oc get modelregistries.modelregistry.opendatahub.io -A -o json 2>/dev/null \
      | python3 -c 'import json,sys; items=json.load(sys.stdin).get("items",[]); values=[]; [(values.append(i.get("metadata",{}).get("namespace","")+"/"+i.get("metadata",{}).get("name","")+"="+("Available" if any(c.get("type")=="Available" and str(c.get("status","")).lower()=="true" for c in i.get("status",{}).get("conditions",[])) else "Not Available"))) for i in items]; print(", ".join(values) or "NONE")' \
      2>/dev/null || printf 'UNKNOWN')
    printf '%-32s %s\n' 'Model Registry components' "${registry_components}"
    printf '%-32s %s\n' 'Model Registry instances' "${registry_instances}"
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

