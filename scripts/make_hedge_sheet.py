"""Sample 50 sentences matched by the hedge lexicon for manual precision labeling.

Fill the `is_hedge` column (1 = real uncertainty hedge, 0 = false match), then
run with --score to print precision.
"""
import csv
import random
import re
import sys
from pathlib import Path

import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.patterns import HEDGE_RE  # noqa: E402

SHEET = ROOT / "results" / "hedge_precision.csv"


def make():
    sentences = []
    for line in (ROOT / "data" / "reports.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        for s in re.split(r"(?<=[.!?])\s+", r["text"]):
            m = HEDGE_RE.search(s)
            if m:
                sentences.append((r["id"], m.group(0).lower(), s))
    random.seed(0)
    picked = random.sample(sentences, 50)
    SHEET.parent.mkdir(exist_ok=True)
    with SHEET.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["report_id", "matched_term", "sentence", "is_hedge"])
        w.writerows([(i, t, s, "") for i, t, s in picked])
    print(f"wrote {SHEET}: fill is_hedge with 1/0, then run with --score")


def score():
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8")))
    labeled = [r for r in rows if r["is_hedge"].strip() in ("0", "1")]
    hits = sum(r["is_hedge"].strip() == "1" for r in labeled)
    print(f"labeled {len(labeled)}/{len(rows)}; precision = {hits / max(len(labeled), 1):.2f}")


if __name__ == "__main__":
    score() if "--score" in sys.argv else make()
