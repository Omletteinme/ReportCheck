"""Generate held-out outputs for verifier evaluation.

Set 1: 20 hedged Open-i reports (disjoint from the first smoke run) x 2 prompt modes
(baseline, structured) -> results/verifier_eval.jsonl.
Set 3 (`--set 3`) holds 3B-model outputs made by scripts/make_eval3.py.
Set 2 (`--set 2`): 20 further reports disjoint from sets 0 and 1, made after the prompt and
verifier fixes -> results/verifier_eval2.jsonl. Greedy decoding. Items are shuffled and
mode-blind in the labeling view (`--show START END`).
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.generate import Generator, build_prompt  # noqa: E402
from src.patterns import HEDGE_RE  # noqa: E402

SET = int(sys.argv[sys.argv.index("--set") + 1]) if "--set" in sys.argv else 1
OUT = ROOT / "results" / ("verifier_eval.jsonl" if SET == 1 else f"verifier_eval{SET}.jsonl")


def generate():
    used = set(re.findall(r"^## (\d+)$", (ROOT / "results" / "smoke_baseline.md").read_text(encoding="utf-8"), re.M))
    if SET == 2:
        used |= {json.loads(l)["report_id"] for l in (ROOT / "results" / "verifier_eval.jsonl").read_text(encoding="utf-8").splitlines()}
    reports = [json.loads(l) for l in (ROOT / "data" / "reports.jsonl").read_text(encoding="utf-8").splitlines()]
    pool = [r for r in reports if HEDGE_RE.search(r["text"]) and r["id"] not in used]
    random.seed(3 if SET == 2 else 2)
    sample = random.sample(pool, 20)
    gen, rows = Generator(), []
    for r in sample:
        for mode in ("baseline", "structured"):
            out = gen.generate(build_prompt(r["text"], mode), max_new_tokens=400)[0]
            rows.append({"item": len(rows), "report_id": r["id"], "mode": mode, "source": r["text"], "output": out})
            print("done", r["id"], mode, flush=True)
    random.shuffle(rows)
    for i, row in enumerate(rows):
        row["item"] = i
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def show(start, end):
    for line in OUT.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if start <= r["item"] < end:
            print(f"### ITEM {r['item']}\nSOURCE: {r['source']}\nOUTPUT: {r['output']}\n")


if __name__ == "__main__":
    if "--show" in sys.argv:
        i = sys.argv.index("--show")
        show(int(sys.argv[i + 1]), int(sys.argv[i + 2]))
    else:
        generate()
