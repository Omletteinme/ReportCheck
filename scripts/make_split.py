"""Write data/split.json: fixed train/test report ids.

test  = every report already used for labeled evaluation (smoke run, verifier sets 1 and 2)
        + random extra hedged/numeric/recommendation Open-i reports up to 100 + synthetic 030-049
train = remaining Open-i reports with a hedge, number or recommendation + synthetic 000-029
Labeled-evaluation reports never enter training, so labeled results stay uncontaminated.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data import labeled_ids, load_reports  # noqa: E402
from src.patterns import HEDGE_RE, NUMBER_RE, RECOMMEND_RE  # noqa: E402

N_TEST_OPENI = 100


def main():
    reports = load_reports()
    openi = [r for r in reports.values() if r["source"] == "openi"]
    eligible = sorted(r["id"] for r in openi
                      if HEDGE_RE.search(r["text"]) or NUMBER_RE.search(r["text"]) or RECOMMEND_RE.search(r["text"]))
    labeled = labeled_ids()
    pool = [i for i in eligible if i not in labeled]
    extra = random.Random(7).sample(pool, N_TEST_OPENI - len(labeled))
    synth = sorted(i for i in reports if i.startswith("synth_"))
    test = sorted(labeled | set(extra)) + synth[30:]
    train = [i for i in eligible if i not in set(test)] + synth[:30]
    (ROOT / "data" / "split.json").write_text(json.dumps({"train": train, "test": test}), encoding="utf-8")
    print(f"train={len(train)} test={len(test)} (labeled={len(labeled)}, eligible openi={len(eligible)})")


if __name__ == "__main__":
    main()
