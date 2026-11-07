"""Smoke run of the sentence-by-sentence system on the first N reports of the 120-report set.

    .venv/Scripts/python scripts/try_sentencewise.py [--limit 10]

Writes results/sentencewise_smoke.jsonl and prints how many sentences were rewritten, why the rest were kept, and the
verifier scores and reading grade of the assembled text against the cached plain draft. Needs the GPU (close games and
stop the demo server first: both load the same models).
"""
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data import load_reports  # noqa: E402
from src.generate import Generator  # noqa: E402
from src.sentencewise import assemble, generate_candidates  # noqa: E402
from src.verify import Verifier, _fk_grade  # noqa: E402

RES = ROOT / "results"


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    limit = ap.parse_args().limit
    cache = [json.loads(line) for line in (RES / "final_eval_candidates.jsonl").read_text(encoding="utf-8").splitlines()][:limit]
    reports, gen, verifier = load_reports(), Generator(), Verifier()
    rows, start = [], time.time()
    for k, c in enumerate(cache, 1):
        source = reports[c["report_id"]]["text"]
        result = assemble(source, generate_candidates(gen, source), verifier.entail_fn)
        plain_score, out_score = verifier.score(source, c["plain"]), verifier.score(source, result["text"])
        rows.append({"report_id": c["report_id"], "source": source, "plain": c["plain"], "output": result["text"],
                     "units": result["units"], "rewritten": result["rewritten"], "total": result["total"],
                     "fk_source": _fk_grade(source), "fk_plain": _fk_grade(c["plain"]), "fk_output": _fk_grade(result["text"]),
                     "plain_total": plain_score.total, "output_total": out_score.total,
                     "plain_entail": plain_score.entail, "output_entail": out_score.entail,
                     "plain_coverage": plain_score.coverage, "output_coverage": out_score.coverage})
        print(f"[{k}/{len(cache)}] report {c['report_id']}: {result['rewritten']}/{result['total']} sentences rewritten "
              f"({time.time() - start:.0f}s)", flush=True)
    (RES / "sentencewise_smoke.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    units = [u for r in rows for u in r["units"]]
    kept = Counter(u["reason"] for u in units if u["status"] == "kept")
    print(f"\nsentences rewritten: {sum(r['rewritten'] for r in rows)}/{len(units)}")
    print("kept because:", dict(kept.most_common()))
    for key in ("fk_source", "fk_plain", "fk_output", "plain_total", "output_total", "plain_entail", "output_entail",
                "plain_coverage", "output_coverage"):
        print(f"mean {key}: {mean([r[key] for r in rows]):.2f}")


if __name__ == "__main__":
    main()
