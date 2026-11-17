"""Compare the T5 systems with the earlier ones on the 120 evaluation reports, without any labeling.

    .venv/Scripts/python scripts/eval_t5.py

Systems: original (labels stripped), plain and best_of_n (from results/final_eval.jsonl), rules (src/plainrules.py),
t5_raw (greedy T5 sentences joined, no checks), hybrid_standard, hybrid_guard and hybrid_strict (T5 sentences accepted only when they pass
every check; otherwise the rule-based sentence; hybrid_guard also rejects a sentence that drops a medical term without reviewed
plain wording; hybrid_strict applies the closed-vocabulary rule instead).

Metrics need no labels: reading grade (Flesch-Kincaid), share of reports at grade 8 or easier, share of reports where the
whole text changes a number, side, severity word, hedge level or negation of the source (plainrules.meaning_changes at
report level: coarse, so it can miss one error in a long report and over-flag a reworded one), and verifier entailment and
coverage (circular for the systems the verifier selected). Writes results/t5_eval.jsonl and results/t5_summary.md.
Needs the GPU (T5 and the NLI model) and models/t5-lay/ from scripts/train_t5.py. Generation is cached in
results/t5_candidates.jsonl, so a rerun only re-scores.
"""
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import textstat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data import load_reports  # noqa: E402
from src.discourse import parse_report  # noqa: E402
from src.plainrules import meaning_changes, simplify, simplify_sentence  # noqa: E402
from src.sentencewise import assemble, generate_candidates  # noqa: E402
from src.t5data import normalize  # noqa: E402
from src.t5gen import T5Generator, t5_prompt  # noqa: E402
from src.text import split_sentences  # noqa: E402
from src.verify import Verifier  # noqa: E402

RES = ROOT / "results"
SYSTEMS = ("original", "plain", "best_of_n", "rules", "t5_raw", "hybrid_standard", "hybrid_guard", "hybrid_strict")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def candidates_for(ids, reports) -> dict[str, list[list[str]]]:
    path = RES / "t5_candidates.jsonl"
    cache = {r["report_id"]: r["candidates"] for r in read_jsonl(path)}
    todo = [i for i in ids if i not in cache]
    if todo:
        gen = T5Generator()
        for k, rid in enumerate(todo, 1):
            cache[rid] = generate_candidates(gen, reports[rid]["text"], n=3, temperature=0.8, max_new_tokens=128, prompt_fn=t5_prompt)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"report_id": rid, "candidates": cache[rid]}) + "\n")
            print(f"generated {k}/{len(todo)}", flush=True)
    return cache


def pct(xs) -> str:
    return f"{100 * sum(xs) / len(xs):.0f}%"


def main():
    final = read_jsonl(RES / "final_eval.jsonl")
    by = {}
    for r in final:
        by.setdefault(r["report_id"], {})[r["system"]] = r
    ids = sorted(by)
    reports = load_reports()
    cands = candidates_for(ids, reports)
    verifier = Verifier()
    fallback = lambda s: simplify_sentence(s)[0]  # noqa: E731
    biolay = {normalize(t) for t in pd.read_parquet(ROOT / "data" / "raw" / "biolaysumm" / "openi_pairs.parquet").radiology_report}

    rows = []
    for rid in ids:
        source = by[rid]["plain"]["source"]
        joined = " ".join(split_sentences(source))
        units = [u.text for u in parse_report(source).units]
        raw = " ".join(c[0] if c else u for u, c in zip(units, cands[rid]))
        hyb = {"hybrid_standard": assemble(source, cands[rid], verifier.entail_fn, fallback, vocab=False),
               "hybrid_guard": assemble(source, cands[rid], verifier.entail_fn, fallback, vocab=False, guard=True),
               "hybrid_strict": assemble(source, cands[rid], verifier.entail_fn, fallback, vocab=True)}
        texts = {"original": joined, "plain": by[rid]["plain"]["output"], "best_of_n": by[rid]["best_of_n"]["output"],
                 "rules": simplify(source)["text"], "t5_raw": raw,
                 "hybrid_standard": hyb["hybrid_standard"]["text"], "hybrid_guard": hyb["hybrid_guard"]["text"],
                 "hybrid_strict": hyb["hybrid_strict"]["text"]}
        for system, text in texts.items():
            score = verifier.score(source, text)
            row = {"report_id": rid, "system": system, "text": text, "fk": textstat.flesch_kincaid_grade(text),
                   "problems": meaning_changes(joined, text), "entail": score.entail, "coverage": score.coverage,
                   "in_biolaysumm": normalize(source) in biolay}
            if system in hyb:
                row["status"] = Counter(u["status"] for u in hyb[system]["units"])
                row["reasons"] = Counter(u["reason"].split(":")[0] for u in hyb[system]["units"] if u["status"] != "rewritten" and u["reason"])
            rows.append(row)
        print(f"scored {rid}", flush=True)
    (RES / "t5_eval.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def table(subset, title):
        lines = [f"### {title}", "", "| system | reading grade | reports at grade 8 or easier | reports where a number, side, severity, hedge or negation changed | entailment (verifier) | coverage (verifier) |",
                 "|---|---|---|---|---|---|"]
        for system in SYSTEMS:
            rs = [r for r in subset if r["system"] == system]
            lines.append(f"| {system} | {statistics.mean(r['fk'] for r in rs):.2f} | {pct([r['fk'] <= 8 for r in rs])} | "
                         f"{pct([bool(r['problems']) for r in rs])} | {statistics.mean(r['entail'] for r in rs):.2f} | "
                         f"{statistics.mean(r['coverage'] for r in rs):.2f} |")
        return lines + [""]

    md = ["# T5 hybrid vs earlier systems (120 reports, no labels)", "",
          "Reading grade is Flesch-Kincaid (lower is easier). The change column is a coarse report-level check, not an error rate. "
          "Entailment and coverage come from the verifier that selected best-of-N, so they are circular for that system.", ""]
    md += table(rows, f"All {len(ids)} reports")
    md += table([r for r in rows if r["in_biolaysumm"]], "Reports that are also in BioLaySumm (never used for training)")
    md += table([r for r in rows if not r["in_biolaysumm"]], "Reports that are not in BioLaySumm")
    for system in ("hybrid_standard", "hybrid_guard", "hybrid_strict"):
        rs = [r for r in rows if r["system"] == system]
        status, reasons = Counter(), Counter()
        for r in rs:
            status.update(r["status"]); reasons.update(r["reasons"])
        total = sum(status.values())
        md += [f"### {system}: where each sentence came from", "",
               ", ".join(f"{k} {v} ({100 * v / total:.0f}%)" for k, v in status.most_common()), "",
               "Most common reasons a T5 sentence was not used: " + ", ".join(f"{k} ({v})" for k, v in reasons.most_common(8)), ""]
    (RES / "t5_summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
