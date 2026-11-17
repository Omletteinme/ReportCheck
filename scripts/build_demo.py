"""Build demo/examples.json from results/t5_eval.jsonl (the T5 hybrid and the rule-based version on 120 unseen reports).

    .venv/Scripts/python scripts/build_demo.py      # needs results/t5_eval.jsonl (scripts/eval_t5.py) and the GPU for the NLI model

Each example carries `selected` (the T5 hybrid with checks) and `plain` (rules only), each with the verifier's explanation.
The 8 reports are picked by fixed rules to show different cases, not by whether the output looks good: biggest reading-level
drop, a number case, a left/right case, the most hedged report, the most and the least model-written outputs, an already
simple report, and one more by reading-level drop.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import numbers  # noqa: E402
from src.glossary import annotate  # noqa: E402
from src.verify import Verifier  # noqa: E402

RES = ROOT / "results"
OUT = ROOT / "demo" / "examples.json"
NOTE = ("Examples were chosen by fixed rules to show different cases, not to be representative or to look good. "
        "The table at the bottom of the page is the fair comparison. Labeled error rates there come from an AI labeler, not humans.")


def main():
    rows = [json.loads(line) for line in (RES / "t5_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    sources = {r["report_id"]: r["source"] for r in map(json.loads, (RES / "final_eval.jsonl").read_text(encoding="utf-8").splitlines())}
    by: dict[str, dict] = {}
    for r in rows:
        by.setdefault(r["report_id"], {})[r["system"]] = r
    items = []
    for rid, d in by.items():
        status = d["hybrid_guard"]["status"]
        total = sum(status.values())
        items.append({"id": rid, "source": sources[rid], "rules": d["rules"]["text"], "hybrid": d["hybrid_guard"]["text"],
                      "drop": d["original"]["fk"] - d["hybrid_guard"]["fk"], "fk": d["original"]["fk"],
                      "model": status.get("rewritten", 0), "rules_n": status.get("rules", 0), "total": total,
                      "model_share": status.get("rewritten", 0) / max(total, 1),
                      "hedged": sum(w in sources[rid].lower() for w in ("possible", "may ", "likely", "suggest", "cannot be", "probable"))})
    chosen: list[tuple[str, dict]] = []

    def take(title, pool, key):
        pool = [i for i in pool if all(i is not x for _, x in chosen)]
        if pool:
            chosen.append((title, max(pool, key=key)))

    take("Biggest reading-level drop", items, lambda i: i["drop"])
    take("A number in the report", [i for i in items if numbers.extract(i["source"])], lambda i: i["drop"])
    take("Left / right in the report", [i for i in items if numbers.sides(i["source"])], lambda i: i["drop"])
    take("Most hedged report", items, lambda i: i["hedged"])
    take("Mostly written by the model", items, lambda i: i["model_share"])
    take("Mostly rule-based (model sentences rejected)", [i for i in items if i["total"] >= 5], lambda i: -i["model_share"])
    take("Already simple", items, lambda i: -i["fk"])
    take("Another case", items, lambda i: i["drop"])

    verifier, examples = Verifier(), []
    for n, (title, i) in enumerate(chosen, 1):
        ex = {"id": i["id"], "source": i["source"], "n_candidates": i["model"], "acceptable": True,
              "units": {"model": i["model"], "rules": i["rules_n"], "total": i["total"]},
              "plain": {"text": i["rules"], "explain": verifier.explain(i["source"], i["rules"])},
              "selected": {"text": i["hybrid"], "explain": verifier.explain(i["source"], i["hybrid"])},
              "title": f"{n}. {title}", "note": NOTE}
        for side in ("plain", "selected"):
            ex[side]["explain"]["sentences"] = annotate(ex[side]["explain"]["sentences"])
        examples.append(ex)
    OUT.write_text(json.dumps(examples), encoding="utf-8")
    print(f"{len(examples)} examples from {len(items)} reports -> {OUT}")
    for e in examples:
        print(f"  {e['title']:<48} report {e['id']:>5}  model sentences {e['units']['model']}/{e['units']['total']}")


if __name__ == "__main__":
    main()
