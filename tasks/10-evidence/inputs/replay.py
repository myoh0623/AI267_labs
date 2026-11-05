"""Deterministic clean-process replay for the synthetic Task 10 artifacts."""

from pathlib import Path
import hashlib
import json
import math

root = Path("/opt/ex267")
model_path = root / "model-current.json"
sample_path = root / "sample.json"
model = json.loads(model_path.read_text(encoding="utf-8"))
sample = json.loads(sample_path.read_text(encoding="utf-8"))
score = sum(a * b for a, b in zip(model["weights"], sample["features"]))
probability = 1.0 / (1.0 + math.exp(-score))
result = {
    "model_version": model["version"],
    "transaction_id": sample["transaction_id"],
    "probability": round(probability, 8),
    "label": int(probability >= model["threshold"]),
}
encoded = (json.dumps(result, sort_keys=True) + "\n").encode()
print(encoded.decode(), end="")
print("sample_inference_sha256=" + hashlib.sha256(encoded).hexdigest())
