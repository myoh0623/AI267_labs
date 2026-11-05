#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$1
namespace=$(lab_task_namespace "${task}")
lab_require_login

namespace_ready=false
for _ in 1 2 3 4 5; do
  if oc get namespace "${namespace}" >/dev/null 2>&1; then
    namespace_ready=true
    break
  fi
  sleep 2
done
[[ "${namespace_ready}" == true ]] || lab_die "Task ${task} is not prepared."
printf 'Task %s · namespace %s\n\n' "${task}" "${namespace}"
oc get all,pvc,configmap,secret,serviceaccount,rolebinding,networkpolicy,route,imagestream,buildconfig \
  -n "${namespace}" 2>/dev/null || true

for resource in \
  notebooks.kubeflow.org \
  datasciencepipelinesapplications.datasciencepipelinesapplications.opendatahub.io \
  workflows.argoproj.io \
  scheduledworkflows.kubeflow.org \
  cronworkflows.argoproj.io \
  inferenceservices.serving.kserve.io \
  hardwareprofiles.infrastructure.opendatahub.io \
  trustyaiservices.trustyai.opendatahub.io \
  lmevaljobs.trustyai.opendatahub.io; do
  oc get "${resource}" -n "${namespace}" 2>/dev/null || true
done

oc get servingruntimes.serving.kserve.io -n "${namespace}" 2>/dev/null || true

if [[ "${task}" == 01 ]]; then
  oc get groups.user.openshift.io devops-wala rhoai-exam-admins 2>/dev/null || true
  oc get auth.services.platform.opendatahub.io auth -o wide 2>/dev/null || \
    oc get auth.services.platform.opendatahub.io auth -n redhat-ods-applications -o wide 2>/dev/null || true
  oc get datasciencecluster -o wide 2>/dev/null || true
fi

if [[ "${task}" == 02 ]]; then
  oc get configmap notebook-controller-culler-config -n redhat-ods-applications 2>/dev/null || true
fi

