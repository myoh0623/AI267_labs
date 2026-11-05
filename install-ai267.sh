#!/usr/bin/env bash
set -Eeuo pipefail

readonly LAB_HOME=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly BIN_DIR="${HOME}/.local/bin"

mkdir -p "${BIN_DIR}"
chmod +x "${LAB_HOME}/ai267"
ln -sfn "${LAB_HOME}/ai267" "${BIN_DIR}/ai267"
printf '설치 완료: %s\n' "${BIN_DIR}/ai267"
printf '사용 예: ai267 04\n'
