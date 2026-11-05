"""Create two small, reproducible TensorBoard runs on the mounted workbench PVC."""

from pathlib import Path
import json
import random

try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError as exc:
    raise SystemExit("Install tensorboard first: python -m pip install tensorboard") from exc


root = Path("/opt/app-root/src/ex267-runs")
root.mkdir(parents=True, exist_ok=True)
for run_name, seed in (("depth-3", 26703), ("depth-7", 26707)):
    random.seed(seed)
    writer = SummaryWriter(str(root / run_name))
    for step in range(10):
        writer.add_scalar("validation/accuracy", 0.70 + step / 100 + random.random() / 100, step)
        writer.add_scalar("validation/loss", 0.40 - step / 100 + random.random() / 100, step)
    writer.close()

(root / "experiment.json").write_text(
    json.dumps({"data_version": "synthetic-fraud-v1", "seed": 267, "runs": 2}, indent=2) + "\n",
    encoding="utf-8",
)
print(root)
