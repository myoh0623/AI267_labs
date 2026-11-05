#!/usr/bin/env bash
set -Eeuo pipefail

readonly CHAPTER_DIR=${1:?Chapter 02 directory is required}
source "${CHAPTER_DIR}/../scripts/demo-common.sh"
cd "${CHAPTER_DIR}"

demo_require_oc_login
demo_require_commands openssl
demo_require_minio_credentials
demo_log "Preparing Chapter 02 with certificate kubeconfig compatibility"

oc apply -f resources/01-project.yaml
oc apply -f resources/02-workbench-dependencies.yaml
oc create secret generic minio \
  -n ai267-ch02-workbench \
  --from-literal=AWS_ACCESS_KEY_ID="${MINIO_ACCESS_KEY}" \
  --from-literal=AWS_SECRET_ACCESS_KEY="${MINIO_SECRET_KEY}" \
  --from-literal=AWS_S3_ENDPOINT='https://minio-api-minio.apps.lab.example.com' \
  --from-literal=AWS_DEFAULT_REGION='us-east-1' \
  --from-literal=AWS_S3_BUCKET='ai267-ch02-workbench' \
  --dry-run=client -o yaml | oc apply -f -
oc label secret minio -n ai267-ch02-workbench \
  opendatahub.io/dashboard=true --overwrite
oc annotate secret minio -n ai267-ch02-workbench \
  openshift.io/display-name='minio' \
  opendatahub.io/connection-type='s3' \
  opendatahub.io/connection-type-protocol='s3' --overwrite

oc apply -f resources/03-workbench.yaml
deadline=$((SECONDS + 300))
while (( SECONDS < deadline )); do
  oc get pod -n ai267-ch02-workbench -l notebook-name=ai267-workbench -o name 2>/dev/null \
    | grep -q . && break
  sleep 2
done
oc wait --for=condition=Ready pod -l notebook-name=ai267-workbench \
  -n ai267-ch02-workbench --timeout=600s
demo_log "Workbench Pod is Ready; OAuth URL check skipped because oc has no bearer token."

oc apply -f resources/04-custom-image-build.yaml
if ! oc get imagestreamtag ai267-workbench:1.0 -n ai267-ch02-workbench >/dev/null 2>&1; then
  oc start-build ai267-workbench -n ai267-ch02-workbench \
    --from-dir=custom-image --follow --wait
fi
oc apply -f resources/05-custom-image-catalog.yaml
oc tag ai267-ch02-workbench/ai267-workbench:1.0 \
  redhat-ods-applications/ai267-workbench:1.0 --reference-policy=local
oc annotate imagestreamtag ai267-workbench:1.0 -n redhat-ods-applications \
  'opendatahub.io/notebook-python-dependencies=[{"name":"seaborn","version":"0.13.2"}]' \
  'opendatahub.io/notebook-software=[{"name":"Python","version":"3.12"}]' --overwrite

"${CHAPTER_DIR}/status-demo.sh"
