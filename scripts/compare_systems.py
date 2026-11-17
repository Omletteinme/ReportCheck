"""Side-by-side table of the paper's metrics for the four systems on the 120 evaluation reports.

    .venv/Scripts/python scripts/compare_systems.py

Systems: plain and best_of_n (the two in the paper), rules (src/plainrules.py), hybrid_guard (T5 + checks + rule fallback).
Labeled rows come from the blind AI labels (results/t5_label_sheets, results/final_eval_labels.csv); the reading grade, simplicity
score and verifier total are recomputed here for all four so the columns are comparable. The verifier total is circular for
best_of_n (the verifier selected it). Writes results/system_comparison.md.
"""
import json
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import t5_labeling  # noqa: E402
from src.text import split_sentences  # noqa: E402
from src.verify import Verifier, _fk_grade  # noqa: E402

RES = ROOT / "results"
SYSTEMS = ("plain", "best_of_n", "rules", "hybrid_guard")
TITLES = {"plain": "Plain AI draft (paper)", "best_of_n": "Best-of-N (paper)", "rules": "Rules only", "hybrid_guard": "T5 hybrid (with guard)"}


def main():
    table, ids, _, _ = t5_labeling.label_table(SYSTEMS)
    rows = [json.loads(line) for line in (RES / "t5_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    text = {(r["report_id"], r["system"]): r["text"] for r in rows}
    source = {r["report_id"]: r["source"] for r in map(json.loads, (RES / "final_eval.jsonl").read_text(encoding="utf-8").splitlines())}
    verifier = Verifier()
    metrics = {s: {"fk": [], "simplicity": [], "total": []} for s in SYSTEMS}
    for rid in ids:
        for s in SYSTEMS:
            out = text[(rid, s)]
            score = verifier.score(source[rid], out)
            metrics[s]["fk"].append(_fk_grade(" ".join(split_sentences(out))))   # the paper's method: labels and markdown stripped
            metrics[s]["simplicity"].append(score.simplicity)
            metrics[s]["total"].append(score.total)
        print("scored", rid, flush=True)
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    rates = {s: {k: mean([table[s][i][k] for i in ids]) for k in ("err", "F", "H", "N", "O", "f")} for s in SYSTEMS}
    lines = ["# Side by side: the paper's systems and the new ones (120 evaluation reports)", "",
             "Error rows are blind AI labels (Claude, not humans); lower is better. Reading grade is Flesch-Kincaid, lower is easier. "
             "Simplicity score: higher is simpler. Verifier total is circular for best-of-N, so do not read it as quality.", "",
             "| metric | " + " | ".join(TITLES[s] for s in SYSTEMS) + " |", "|---|" + "---|" * len(SYSTEMS)]
    for key, name in (("err", "Any H/N/F error"), ("F", "Unsupported content (F)"), ("H", "Hedge error (H)"),
                      ("N", "Number/side error (N)"), ("O", "Key finding omitted (O)")):
        lines.append(f"| {name} | " + " | ".join(f"{rates[s][key]:.2f}" for s in SYSTEMS) + " |")
    lines.append("| Flesch-Kincaid grade | " + " | ".join(f"{mean(metrics[s]['fk']):.2f}" for s in SYSTEMS) + " |")
    lines.append("| Reports at grade 8 or easier | " + " | ".join(f"{sum(x <= 8 for x in metrics[s]['fk']) / len(ids):.0%}" for s in SYSTEMS) + " |")
    lines.append("| Simplicity score | " + " | ".join(f"{mean(metrics[s]['simplicity']):.2f}" for s in SYSTEMS) + " |")
    lines.append("| Verifier total (circular for best-of-N) | " + " | ".join(f"{mean(metrics[s]['total']):.2f}" for s in SYSTEMS) + " |")
    lines += ["", "The first two columns are Table II of the paper (the same numbers, recomputed). The last two are new and were not "
              "in the paper. One AI labeler, no clinician; the rule table has not been clinically reviewed; the T5 model was trained on "
              "AI-written plain-language text with no stated licence."]
    out = "\n".join(lines) + "\n"
    (RES / "system_comparison.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
