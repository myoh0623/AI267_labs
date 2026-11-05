#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/lab-common.sh"

task=$1
shift
lab_require_login
lab_require_command python3
exec python3 "${SCRIPT_DIR}/grade.py" "${task}" "$@"

