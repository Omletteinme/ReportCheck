"""Report loading and the fixed train/test split (data/split.json, written by scripts/make_split.py)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _read(name: str) -> list[dict]:
    return [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines()]


def load_reports() -> dict[str, dict]:
    """Open-i reports plus the synthetic ones, keyed by id."""
    return {r["id"]: r for r in _read("reports.jsonl") + _read("synthetic.jsonl")}


def load_split() -> dict[str, list[str]]:
    return json.loads((DATA / "split.json").read_text(encoding="utf-8"))


def labeled_ids() -> set[str]:
    """Report ids already used in labeled evaluation (smoke run, verifier sets 1 and 2); never train on these."""
    import re

    res = ROOT / "results"
    ids = set(re.findall(r"^## (\d+)$", (res / "smoke_baseline.md").read_text(encoding="utf-8"), re.M))
    for name in ("verifier_eval.jsonl", "verifier_eval2.jsonl"):
        ids |= {json.loads(line)["report_id"] for line in (res / name).read_text(encoding="utf-8").splitlines()}
    return ids
