#!/usr/bin/env bash
set -Eeuo pipefail

readonly LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

printf '[validate] Bash syntax\n'
while IFS= read -r script; do
  bash -n "${script}"
done < <(find "${LAB_ROOT}" -path "${LAB_ROOT}/.git" -prune -o -type f -name '*.sh' -print | sort)

printf '[validate] Python syntax\n'
python3 - "${LAB_ROOT}" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
paths = sorted(path for path in root.rglob("*.py") if ".git" not in path.parts)
for path in paths:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print(f"[validate] parsed {len(paths)} Python files")
PY

printf '[validate] Catalog and task bundle\n'
python3 - "${LAB_ROOT}" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
rows = []
for line in (root / "tasks" / "catalog.tsv").read_text(encoding="utf-8").splitlines():
    if not line or line.startswith("#"):
        continue
    fields = line.split("\t")
    assert len(fields) == 6, fields
    rows.append(fields)

assert len(rows) == 12, len(rows)
assert [row[0] for row in rows] == [f"{number:02d}" for number in range(1, 13)]
for column in (0, 1):
    values = [row[column] for row in rows]
    assert len(values) == len(set(values)), values

allowed_labs = {
    "intro-projects",
    "workbench-creating",
    "workbench-connections",
    "workbench-working",
    "workbench-custom",
    "serving-openvino",
    "dspa-intro",
    "dspa-kubeflow",
    "dspa-elyra",
}
assert {row[2] for row in rows} <= allowed_labs
for task_id, slug, *_ in rows:
    path = root / "tasks" / f"{task_id}-{slug}" / "README.md"
    assert path.is_file(), path
print("[validate] 12 task bundles passed")
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

for task_id, task in module["TASKS"].items():
    results = module["GRADERS"][task_id](EmptyOc(), task.namespace)
    assert len(results) == 5, task_id
    assert sum(item.points for item in results) == task.points == 100, task_id
    assert len({item.check_id for item in results}) == 5, task_id
    assert not any(item.passed for item in results), task_id
print("[validate] 12 grader point contracts passed")
PY

printf '[validate] Grader regression fixtures\n'
python3 -m unittest discover -s "${LAB_ROOT}/scripts" -p 'test_grade_regressions.py'

printf '[validate] Fixture cleanup safety regressions\n'
python3 -m unittest discover -s "${LAB_ROOT}/scripts" -p 'test_fixture_safety.py'

printf '[validate] Lifecycle regression\n'
bash "${LAB_ROOT}/scripts/test-lifecycle.sh"

printf '[validate] Source coverage\n'
python3 - "${LAB_ROOT}" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
source_map = (root / "SOURCE-MAP.md").read_text(encoding="utf-8")
expected = [
    "00-00 ReadMe.md",
    "00-01 Theory.md",
    "01-02 Installation of RHOAI.md",
    "01-0301 UserPermission.md",
    "01-0302 Usermanagement.md",
    "02-01-workbench-size.md",
    "02-03 Workbenchsize.md",
    "02-06 Data Connections.md",
    "03-03 ModifyWorkbench.md",
    "05-00 Create a Custom Notebook Image.md",
    "05-03 CustomImage.md",
    "06-01 Collaboration with Jupyter Notebooks.md",
    "06-03 Add S3.md",
    "07-03 Modal.md",
    "08-03 Creating Pipelines with the KubeFlow.md",
    "09-01 Create Pipeline by Elyra.md",
    "09-03 Create pipeline with Elyra.md",
]
for name in expected:
    assert source_map.count(f"`{name}`") == 1, name
print("[validate] 17/17 source documents mapped")
PY

printf '[validate] No stale executable contracts\n'
if command -v rg >/dev/null 2>&1; then
  stale_output=$(rg -n --glob '!validate-local.sh' 'lab start -t AI26|lab finish -t AI26|ex267-t0|ai267-ch0' \
    "${LAB_ROOT}/scripts" "${LAB_ROOT}/tasks" || true)
else
  stale_output=$(grep -RInE --exclude=validate-local.sh 'lab start -t AI26|lab finish -t AI26|ex267-t0|ai267-ch0' \
    "${LAB_ROOT}/scripts" "${LAB_ROOT}/tasks" || true)
fi
if [[ -n "${stale_output}" ]]; then
  printf '%s\n' "${stale_output}"
  printf '[validate] stale 2.x or parallel-namespace contract found\n' >&2
  exit 1
fi

printf '[validate] YAML parse\n'
python3 - "${LAB_ROOT}" <<'PY'
from pathlib import Path
import sys
import yaml

root = Path(sys.argv[1])
count = 0
for path in sorted(root.rglob("*.yaml")):
    if ".git" in path.parts:
        continue
    with path.open(encoding="utf-8") as stream:
        documents = list(yaml.safe_load_all(stream))
    if not documents or any(document is None for document in documents):
        raise SystemExit(f"empty YAML document: {path}")
    count += len(documents)
print(f"[validate] parsed {count} YAML documents")
PY

printf '[validate] PASS\n'
