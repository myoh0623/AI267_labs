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

printf '[validate] Expanded grader positive fixtures\n'
python3 "${LAB_ROOT}/tests/test_extended_graders.py"

printf '[validate] V2.13 source coverage\n'
python3 - "${LAB_ROOT}" <<'PY'
from pathlib import Path
import runpy
import sys
import yaml

root = Path(sys.argv[1])
coverage = yaml.safe_load((root / "source-coverage.yaml").read_text(encoding="utf-8"))
entries = coverage["entries"]
expected = int(coverage["source"]["expected_markdown_files"])
paths = [entry["path"] for entry in entries]
assert len(entries) == expected == 34, (len(entries), expected)
assert len(paths) == len(set(paths)), "duplicate source path"
assert paths[0] == "00-00 ReadMe.md"
assert paths[-1] == "09-03 Create pipeline with Elyra.md"

inventory = {}
for line in (root / "source-inventory.sha256").read_text(encoding="utf-8").splitlines():
    digest, path = line.split("  ", 1)
    assert len(digest) == 64 and all(char in "0123456789abcdef" for char in digest), path
    assert path not in inventory, path
    inventory[path] = digest
assert set(inventory) == set(paths), "source hash inventory and coverage paths differ"

grader = runpy.run_path(str(root / "scripts" / "grade.py"), run_name="coverage_contract_test")

class EmptyOc:
    def get(self, *args, **kwargs):
        return None
    def list(self, *args, **kwargs):
        return []
    def list_all(self, *args, **kwargs):
        return []

known_checks = set()
for task, (namespace, _, _) in grader["TASKS"].items():
    known_checks.update(item.check_id for item in grader["GRADERS"][task](EmptyOc(), namespace))

for entry in entries:
    if entry["type"] == "actionable":
        assert entry.get("task") in grader["TASKS"], entry["path"]
        checks = entry.get("checks", [])
        assert checks, entry["path"]
        unknown = set(checks) - known_checks
        assert not unknown, (entry["path"], sorted(unknown))
    elif entry["type"] == "guidance":
        destinations = entry.get("destinations", [])
        assert destinations, entry["path"]
        for destination in destinations:
            assert (root / destination).exists(), (entry["path"], destination)
    else:
        raise AssertionError((entry["path"], entry["type"]))

table = (root / "V213-COVERAGE.md").read_text(encoding="utf-8")
for path in paths:
    assert f"`{path}`" in table, path
print(f"[validate] {len(entries)}/{expected} source Markdown mappings and pinned hashes passed")
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
