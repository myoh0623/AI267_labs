#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$1
namespace=$(lab_task_namespace "${task}")
lab_require_login

oc get namespace "${namespace}" >/dev/null 2>&1 || lab_die "Task ${task} is not prepared."
printf 'Task %s · namespace %s\n\n' "${task}" "${namespace}"
oc get all,pvc,configmap,secret,serviceaccount,rolebinding,networkpolicy -n "${namespace}" 2>/dev/null || true

for resource in \
  notebooks.kubeflow.org \
  datasciencepipelinesapplications.datasciencepipelinesapplications.opendatahub.io \
  workflows.argoproj.io \
  inferenceservices.serving.kserve.io \
  trustyaiservices.trustyai.opendatahub.io \
  lmevaljobs.trustyai.opendatahub.io; do
  oc get "${resource}" -n "${namespace}" 2>/dev/null || true
done

