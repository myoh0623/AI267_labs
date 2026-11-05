"""Prepare the small OpenBookQA and GPT-2 tokenizer cache for offline LM-Eval."""

from pathlib import Path
import json
import os
import shutil

from datasets import load_dataset
from transformers import AutoTokenizer

hf_home = Path(os.environ["HF_HOME"])
dataset = load_dataset("openbookqa", "main")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Hugging Face snapshots use relative symlinks into hub/blobs.  S3 object
# stores do not preserve symlinks, so materialize them before syncing.
for path in sorted(hf_home.rglob("*")):
    if path.is_symlink():
        target = path.resolve(strict=True)
        path.unlink()
        shutil.copy2(target, path)

marker = {
    "dataset": "openbookqa@388097ea7776314e93a529163e0fea805b8a6454",
    "splits": {name: len(split) for name, split in dataset.items()},
    "tokenizer": tokenizer.name_or_path,
    "datasets_version": "3.1.0",
    "transformers_version": "4.48.0",
    "cache_format": "materialized-v2",
}
(hf_home / "ex267-cache-ready.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
print(json.dumps(marker, sort_keys=True))
