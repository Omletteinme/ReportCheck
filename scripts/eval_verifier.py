"""Evaluate the verifier against labeled outputs.

dev  = 20 baseline outputs from the first smoke run (results/smoke_baseline*.md)
test = 40 held-out outputs (results/verifier_eval.jsonl + verifier_eval_labels.csv)

All labels were assigned by Claude, test labels blind to prompt mode and verifier scores.
AUC = P(a randomly chosen clean output outscores a randomly chosen errored one); 0.5 = chance.
Component checks: certainty vs H (hedge error), numbers vs N (number/laterality), entail vs F (fabrication),
total vs any of H/N/F. 95% CIs by bootstrap over outputs.
"""
import csv
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.agreement import auc  # noqa: E402
from src.verify import Verifier  # noqa: E402

RES = ROOT / "results"


def load_dev():
    pairs = {}
    for block in (RES / "smoke_baseline.md").read_text(encoding="utf-8").split("\n## ")[1:]:
        rid = block.split("\n")[0].strip()
        pairs[rid] = (re.search(r"\*\*Source:\*\* (.*?)\n", block).group(1),
                      block.split("**Output:**")[1].split("\n- numbers kept")[0].strip())
    rows = []
    for line in (RES / "smoke_baseline_labels.md").read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in line.strip("|").split("|")]
        if len(c) >= 4 and c[0].isdigit():
            rows.append({"id": c[0], "mode": "baseline", "source": pairs[c[0]][0], "output": pairs[c[0]][1],
                         "H": c[1] == "H", "N": c[2] == "N", "F": c[3] == "F"})
    return rows


def load_test(suffix=""):
    labels = {int(r["item"]): r for r in csv.DictReader((RES / f"verifier_eval{suffix}_labels.csv").open(encoding="utf-8"))}
    rows = []
    for line in (RES / f"verifier_eval{suffix}.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        lab = labels[r["item"]]
        rows.append({"id": r["item"], "mode": r["mode"], "source": r["source"], "output": r["output"],
                     "H": lab["H"] == "1", "N": lab["N"] == "1", "F": lab["F"] == "1"})
    return rows


def boot_ci(scores, bad, n=500):
    rng, vals = random.Random(0), []
    for _ in range(n):
        idx = [rng.randrange(len(scores)) for _ in scores]
        a = auc([scores[i] for i in idx], [bad[i] for i in idx])
        if a == a:
            vals.append(a)
    vals.sort()
    return vals[int(.025 * len(vals))], vals[int(.975 * len(vals))]


def report(name, rows, verifier):
    scored = [verifier.score(r["source"], r["output"]) for r in rows]
    any_bad = [r["H"] or r["N"] or r["F"] for r in rows]
    print(f"\n== {name}: n={len(rows)}, errored={sum(any_bad)}, clean={len(rows) - sum(any_bad)}")
    checks = [("total vs any error", [s.total for s in scored], any_bad),
              ("certainty vs H", [s.certainty for s in scored], [r["H"] for r in rows]),
              ("numbers vs N", [s.numbers for s in scored], [r["N"] for r in rows]),
              ("entail vs F", [s.entail for s in scored], [r["F"] for r in rows])]
    for label, sc, bad in checks:
        a = auc(sc, bad)
        lo, hi = boot_ci(sc, bad) if a == a else (float("nan"),) * 2
        print(f"  AUC {label:<20} {a:.2f}  (95% CI {lo:.2f}-{hi:.2f}, positives={sum(bad)})")
    return scored


def main():
    v = Verifier()
    dev, test, fresh, set3 = load_dev(), load_test(), load_test("2"), load_test("3")
    report("dev (smoke run, baseline prompt)", dev, v)
    scored = report("test (held-out at first scoring)", test, v)
    report("dev+test combined", dev + test, v)
    scored2 = report("fresh set 2 (labeled blind, never used for tuning)", fresh, v)
    scored3 = report("set 3 (Qwen2.5-3B outputs, labeled blind, not used for tuning)", set3, v)
    print("\n== prompt mode on test (same 20 reports each; labels, then verifier total)")
    for name, rows, sc in (("set 1 (old prompt)", test, scored), ("set 2 (new prompt)", fresh, scored2),
                           ("set 3 (3B)", set3, scored3)):
        for mode in dict.fromkeys(r["mode"] for r in rows):
            idx = [i for i, r in enumerate(rows) if r["mode"] == mode]
            n = len(idx)
            rates = {k: sum(rows[i][k] for i in idx) / n for k in "HNF"}
            mean = sum(sc[i].total for i in idx) / n
            print(f"  {name:<20} {mode:<14} n={n}  H={rates['H']:.2f} N={rates['N']:.2f} F={rates['F']:.2f}  mean total={mean:.3f}")

if __name__ == "__main__":
    main()
