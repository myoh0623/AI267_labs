#!/usr/bin/env bash
set -Eeuo pipefail

readonly LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

printf '[validate] Bash syntax\n'
while IFS= read -r script; do
  bash -n "${script}"
done < <(find "${LAB_ROOT}" -type f -name '*.sh' -print | sort)

printf '[validate] Python syntax\n'
python3 - "${LAB_ROOT}" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
paths = [
    root / "scripts" / "grade.py",
    *sorted((root / "vendor").rglob("*.py")),
    *sorted((root / "tasks").rglob("*.py")),
]
for path in paths:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print(f"[validate] parsed {len(paths)} Python files")
PY

printf '[validate] Grader contracts\n'
python3 - "${LAB_ROOT}/scripts/grade.py" <<'PY'
import runpy
import sys

module = runpy.run_path(sys.argv[1], run_name="grade_contract_test")

class EmptyOc:
    def get(self, *args, **kwargs):
        return None
    def list(self, *args, **kwargs):
        return []
    def list_all(self, *args, **kwargs):
        return []

for task, (namespace, maximum, _) in module["TASKS"].items():
    results = module["GRADERS"][task](EmptyOc(), namespace)
    assert sum(item.points for item in results) == maximum, task
    assert not any(item.passed for item in results), task
print("[validate] 10 grader point contracts passed")
PY

printf '[validate] YAML parse\n'
python3 - "${LAB_ROOT}" <<'PY'
from pathlib import Path
import sys
import yaml

root = Path(sys.argv[1])
count = 0
for path in sorted(root.rglob("*.yaml")):
    with path.open(encoding="utf-8") as stream:
        docs = list(yaml.safe_load_all(stream))
    if not docs or any(doc is None for doc in docs):
        raise SystemExit(f"empty YAML document: {path}")
    count += len(docs)
print(f"[validate] parsed {count} YAML documents")
PY

printf '[validate] Task bundle completeness\n'
for task in 01-foundation 02-workbench 03-pipeline 04-predictive-serving 05-vllm-gpu 06-model-registry 07-monitoring 08-optimization 09-rag 10-evidence; do
  test -f "${LAB_ROOT}/tasks/${task}/README.md"
  test -f "${LAB_ROOT}/tasks/${task}/resources/seed.yaml"
done

printf '[validate] PASS\n'
