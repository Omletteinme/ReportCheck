"""Build demo/examples.json from results/heldout_eval.jsonl (plain LLM vs best-of-N on held-out reports).

Picks up to 8 reports to show different cases; the selection is by rule, not by cherry-picking favourable
results: biggest verifier gain, a number case, a restored hedge, a left/right case, a case where the checker
found nothing better, a clean case, and the most hedged report. Works on partial data (for testing the page).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import numbers  # noqa: E402
from src.glossary import annotate  # noqa: E402
from src.verify import Verifier  # noqa: E402

SRC = ROOT / "results" / "heldout_eval.jsonl"
OUT = ROOT / "demo" / "examples.json"
NOTE = ("Examples were chosen by fixed rules to show different cases, not to be representative. "
        "The held-out table at the bottom of the page is the fair comparison.")


def issues(explain: dict) -> int:
    s = explain["summary"]
    return (len(s["unsupported_numbers"]) + len(s["missing_numbers"]) + len(s["wrong_sides"])
            + len(s["wrong_qualifiers"]) + len(s["dropped_levels"])
            + sum(any(f["kind"] == "unsupported" for f in x["flags"]) for x in explain["sentences"]))


def main():
    rows = [json.loads(line) for line in SRC.read_text(encoding="utf-8").splitlines()]
    by_report: dict[str, dict] = {}
    for r in rows:
        by_report.setdefault(r["report_id"], {})[r["system"]] = r
    verifier, items = Verifier(), []
    for rid, pair in by_report.items():
        if len(pair) < 2:
            continue
        plain, best = pair["plain"], pair["best_of_n"]
        ex = {"id": rid, "source": plain["source"], "n_candidates": best.get("n_candidates", 0),
              "acceptable": best.get("acceptable", False),
              "plain": {"text": plain["output"], "explain": verifier.explain(plain["source"], plain["output"])},
              "selected": {"text": best["output"], "explain": verifier.explain(plain["source"], best["output"])}}
        for side in ("plain", "selected"):
            ex[side]["explain"]["sentences"] = annotate(ex[side]["explain"]["sentences"])
        ex["delta"] = ex["selected"]["explain"]["score"]["total"] - ex["plain"]["explain"]["score"]["total"]
        ex["levels"] = ex["plain"]["explain"]["summary"]["source_levels"]
        ex["hedged"] = sum(s["level"] != "definite" for s in ex["plain"]["explain"]["source_sentences"])
        items.append(ex)

    chosen: list[tuple[str, dict]] = []

    def take(title: str, candidates: list[dict], key):
        pool = [c for c in candidates if all(c is not x for _, x in chosen)]
        if pool:
            chosen.append((title, max(pool, key=key)))

    has_number = [i for i in items if numbers.extract(i["source"])]
    restored = [i for i in items if i["plain"]["explain"]["summary"]["dropped_levels"]
                and not i["selected"]["explain"]["summary"]["dropped_levels"]]
    sided = [i for i in items if numbers.sides(i["source"])]
    take("Biggest gain from checking", items, lambda i: i["delta"])
    take("A number in the report", has_number, lambda i: i["delta"])
    take("Hedge restored", restored, lambda i: i["delta"])
    take("Left / right in the report", sided, lambda i: i["delta"])
    take("Checker found nothing better", [i for i in items if i["delta"] <= 0], lambda i: -i["delta"])
    take("Both drafts clean", [i for i in items if issues(i["plain"]["explain"]) + issues(i["selected"]["explain"]) == 0],
         lambda i: i["delta"])
    take("Most hedged report", items, lambda i: i["hedged"])
    take("Another case", items, lambda i: i["delta"])

    examples = []
    for n, (title, ex) in enumerate(chosen, 1):
        ex = {k: v for k, v in ex.items() if k not in ("delta", "levels", "hedged")}
        examples.append({**ex, "title": f"{n}. {title}", "note": NOTE})
    OUT.write_text(json.dumps(examples), encoding="utf-8")
    print(f"{len(examples)} examples from {len(items)} reports -> {OUT}")
    for e in examples:
        print(f"  {e['title']:<36} report {e['id']:>5}  plain {e['plain']['explain']['score']['total']:.2f} "
              f"selected {e['selected']['explain']['score']['total']:.2f}")


if __name__ == "__main__":
    main()
