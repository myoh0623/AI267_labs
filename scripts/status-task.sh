#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$1
lab_load_task "${task}"
lab_require_command lab
lab_require_login

printf 'Task %s · %s\n' "${TASK_ID}" "${TASK_TITLE}"
printf '공식 Lab: %s\n' "${TASK_LAB}"
printf '프로젝트: %s\n\n' "${TASK_NAMESPACE}"
lab_course_status "${TASK_LAB}"

if ! oc get namespace "${TASK_NAMESPACE}" >/dev/null 2>&1; then
  printf '\n프로젝트 %s가 아직 없습니다.\n' "${TASK_NAMESPACE}"
  exit 0
fi

printf '\n[Kubernetes resources]\n'
oc get pod,service,statefulset,pvc,configmap,secret,rolebinding,route,imagestream \
  -n "${TASK_NAMESPACE}" 2>/dev/null || true

for resource in \
  notebooks.kubeflow.org \
  hardwareprofiles.infrastructure.opendatahub.io \
  datasciencepipelinesapplications.datasciencepipelinesapplications.opendatahub.io \
  pipelines.pipelines.kubeflow.org \
  pipelineversions.pipelines.kubeflow.org \
  workflows.argoproj.io \
  scheduledworkflows.kubeflow.org \
  cronworkflows.argoproj.io \
  inferenceservices.serving.kserve.io; do
  oc get "${resource}" -n "${TASK_NAMESPACE}" 2>/dev/null || true
done

if [[ "${task}" == 02 ]]; then
  printf '\n[RHOAI access]\n'
  oc get auth.services.platform.opendatahub.io auth -o jsonpath='{.spec}' 2>/dev/null || true
  printf '\n'
  oc get group devops-wala ai267-admins 2>/dev/null || true
fi
