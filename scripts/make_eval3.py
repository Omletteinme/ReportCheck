"""Build verifier set 3 from the Qwen2.5-3B outputs (results/_size_*.json): 20 set-2 reports x 2 rule sets.

Shuffled, mode-blind labeling view: `python scripts/gen_verifier_eval.py --set 3 --show START END`.
"""
import json
import random
from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "results"
ids = list(dict.fromkeys(json.loads(l)["report_id"] for l in (RES / "verifier_eval2.jsonl").read_text(encoding="utf-8").splitlines()))
rows = []
for mode, name in (("3b_old_rules", "old_rules"), ("3b_mild_rules", "mild_rules")):
    for rid, (source, output) in zip(ids, json.loads((RES / f"_size_Qwen2.5-3B-Instruct_{name}.json").read_text())):
        rows.append({"report_id": rid, "mode": mode, "source": source, "output": output})
random.Random(11).shuffle(rows)
for i, r in enumerate(rows):
    r["item"] = i
(RES / "verifier_eval3.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
print(len(rows), "items")
