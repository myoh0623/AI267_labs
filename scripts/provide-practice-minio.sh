#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$(lab_normalize_task "${1:-}") || lab_die "Task 번호를 지정하세요: 01, 03, 04"
case "${task}" in
  01) bucket=ex267-task01 ;;
  03) bucket=ex267-task03 ;;
  04) bucket=ex267-task04 ;;
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

printf '\n[ai267] 시험 제공값 준비 완료\n'
printf '  Console: Workloads -> Secrets -> exam-provided-minio\n'
printf '  Namespace: %s\n' "${namespace}"
printf '  Bucket: %s (생성 완료)\n' "${bucket}"
printf '  주의: 채점 대상 Secret은 일부러 REPLACE_ME 상태입니다. 문제 지침대로 직접 완성하세요.\n\n'
