"""Build verifier-ranked candidates and DPO preference pairs for the training split.

Stage 1 (GPU, resumable): sample candidates per train report, score them, append to data/candidates.jsonl.
Stage 2 (CPU): pick chosen/rejected with src.bestofn.preference_pair -> data/pairs.jsonl.

Usage: python scripts/build_pairs.py [--limit N] [--n 8] [--pairs-only]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.bestofn import Candidate, acceptable, preference_pair, rank, sample_candidates  # noqa: E402
from src.data import load_reports, load_split  # noqa: E402
from src.generate import Generator, build_prompt  # noqa: E402
from src.verify import Score, Verifier  # noqa: E402

CANDIDATES = ROOT / "data" / "candidates.jsonl"
PAIRS = ROOT / "data" / "pairs.jsonl"
SCORE_FIELDS = ("entail", "numbers", "certainty", "simplicity", "total")


def read_candidates() -> list[dict]:
    if not CANDIDATES.exists():
        return []
    return [json.loads(l) for l in CANDIDATES.read_text(encoding="utf-8").splitlines()]


def generate_stage(limit: int, n: int):
    reports, train = load_reports(), load_split()["train"]
    done = {r["id"] for r in read_candidates()}
    todo = [i for i in train if i not in done][: limit or None]
    gen, verifier = Generator(), Verifier()
    start = time.time()
    for k, rid in enumerate(todo, 1):
        source = reports[rid]["text"]
        ranked = rank(verifier, source, sample_candidates(gen, source, n))
        row = {"id": rid, "source": source,
               "candidates": [{"text": c.text, **{f: getattr(c.score, f) for f in SCORE_FIELDS}} for c in ranked]}
        with CANDIDATES.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(f"[{k}/{len(todo)}] {rid}: {len(ranked)} candidates, {(time.time() - start) / k:.0f}s/report", flush=True)


def pairs_stage():
    rows, pairs, n_ok = read_candidates(), [], 0
    for row in rows:
        ranked = [Candidate(c["text"], Score(**{f: c[f] for f in SCORE_FIELDS})) for c in row["candidates"]]
        n_ok += any(acceptable(c.score) for c in ranked)
        if pair := preference_pair(ranked):
            chosen, rejected = pair
            pairs.append({"id": row["id"], "prompt": build_prompt(row["source"], "structured"),
                          "chosen": chosen.text, "rejected": rejected.text,
                          "chosen_total": chosen.score.total, "rejected_total": rejected.score.total})
    PAIRS.write_text("\n".join(json.dumps(p) for p in pairs) + ("\n" if pairs else ""), encoding="utf-8")
    words = lambda key: sum(len(p[key].split()) for p in pairs) / max(len(pairs), 1)  # noqa: E731
    gap = sum(p["chosen_total"] - p["rejected_total"] for p in pairs) / max(len(pairs), 1)
    print(f"reports={len(rows)} with_acceptable={n_ok} pairs={len(pairs)} mean_gap={gap:.3f} "
          f"words chosen={words('chosen'):.0f} rejected={words('rejected'):.0f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--pairs-only", action="store_true")
    args = ap.parse_args()
    if not args.pairs_only:
        generate_stage(args.limit, args.n)
    pairs_stage()
