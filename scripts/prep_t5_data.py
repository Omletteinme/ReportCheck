"""Build sentence-level training data for the T5 simplifier from the BioLaySumm Open-i pairs.

    .venv/Scripts/python scripts/prep_t5_data.py

Needs data/raw/biolaysumm/openi_pairs.parquet (the Open-i rows of BioLaySumm/BioLaySumm2025-LaymanRRG-opensource-track).
Writes data/raw/t5/train.jsonl and val.jsonl ({"rid", "source", "target"}). The plain-language text was written by an
LLM and its licence is not stated, so these files stay out of git (data/raw/ is ignored).

Reports in our 120-report evaluation set, in any labeled set, or in the fixed test split are never used for training.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data import labeled_ids, load_reports, load_split  # noqa: E402
from src.t5data import normalize, sentence_pairs, split_by_id  # noqa: E402

OUT = ROOT / "data" / "raw" / "t5"
MAX_TARGETS = 4   # distinct plain-language versions kept per source sentence, so stock sentences do not dominate


def main():
    pairs = pd.read_parquet(ROOT / "data" / "raw" / "biolaysumm" / "openi_pairs.parquet")
    pairs = pairs[pairs.layman_report.str.strip() != ""]
    print(f"BioLaySumm Open-i pairs with a plain-language report: {len(pairs)}")
    ours = {normalize(r["text"]): rid for rid, r in load_reports().items() if r["source"] == "openi"}
    pairs = pairs.assign(rid=[ours.get(normalize(t)) for t in pairs.radiology_report])
    print(f"  matched to one of our Open-i reports: {int(pairs.rid.notna().sum())}")

    final = {json.loads(line)["report_id"] for line in (ROOT / "results" / "final_eval.jsonl").read_text(encoding="utf-8").splitlines()}
    banned = final | labeled_ids() | set(load_split()["test"])
    pairs = pairs[pairs.rid.notna() & ~pairs.rid.isin(banned)]
    print(f"  after dropping evaluation, labeled and test-split reports: {len(pairs)} pairs, {pairs.rid.nunique()} reports")

    seen, per_source, rows, equal = set(), {}, [], 0
    for rid, source, lay in zip(pairs.rid, pairs.radiology_report, pairs.layman_report):
        got = sentence_pairs(source, lay)
        equal += bool(got)
        for s, t in got:
            if (s, t) in seen or per_source.get(s, 0) >= MAX_TARGETS:   # the same stock sentence appears in many reports
                continue
            seen.add((s, t))
            per_source[s] = per_source.get(s, 0) + 1
            rows.append({"rid": rid, "source": s, "target": t})
    print(f"  reports that yielded at least one sentence pair: {equal}")
    print(f"  distinct sentence pairs that pass the meaning checks (at most {MAX_TARGETS} per source sentence): "
          f"{len(rows)} over {len(per_source)} source sentences")
    train, val = split_by_id(rows)
    assert not ({r["rid"] for r in train} & {r["rid"] for r in val})
    assert not ({r["rid"] for r in train + val} & banned), "a banned report leaked into the training data"
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part in (("train", train), ("val", val)):
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in part), encoding="utf-8")
    print(f"wrote {len(train)} train and {len(val)} validation pairs to {OUT}")


if __name__ == "__main__":
    main()
