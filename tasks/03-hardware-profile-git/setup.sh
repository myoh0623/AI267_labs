#!/usr/bin/env bash
set -Eeuo pipefail

oc apply -f - <<'EOF'
apiVersion: infrastructure.opendatahub.io/v1
kind: HardwareProfile
metadata:
  name: large
  namespace: workbench-creating
  annotations:
    opendatahub.io/disabled: "false"
    opendatahub.io/display-name: Large
spec:
  identifiers:
    - identifier: cpu
      displayName: CPU
      resourceType: CPU
      minCount: "4"
      defaultCount: "4"
      maxCount: "4"
    - identifier: memory
      displayName: Memory
      resourceType: Memory
      minCount: 16Gi
      defaultCount: 16Gi
      maxCount: 16Gi
---
apiVersion: infrastructure.opendatahub.io/v1
kind: HardwareProfile
metadata:
  name: xlarge
  namespace: workbench-creating
  annotations:
    opendatahub.io/disabled: "false"
    opendatahub.io/display-name: X Large
spec:
  identifiers:
    - identifier: cpu
      displayName: CPU
      resourceType: CPU
      minCount: "8"
      defaultCount: "8"
      maxCount: "8"
    - identifier: memory
      displayName: Memory
      resourceType: Memory
      minCount: 32Gi
      defaultCount: 32Gi
      maxCount: 32Gi
EOF
