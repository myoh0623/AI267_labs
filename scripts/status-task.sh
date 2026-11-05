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

oc get servingruntimes.serving.kserve.io -n "${namespace}" 2>/dev/null || true

