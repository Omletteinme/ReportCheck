"""Plain LLM vs best-of-N with the verifier, on held-out reports.

    python scripts/eval_bestofn.py [--reports heldout|set2]            # generate (GPU, resumable)
    python scripts/eval_bestofn.py --reports heldout --show 0 10       # blind labeling view
    python scripts/eval_bestofn.py --reports heldout --score           # metrics, CIs, summary file
    python scripts/eval_bestofn.py --reports final                     # 120 reports, caches every candidate (overnight GPU run)
    python scripts/eval_bestofn.py --reports final --rescore           # re-pick from cached candidates after a verifier change (no generation)

heldout = the 40 held-out Open-i reports (in split["test"], never in a labeled set or in training).
set2    = the 20 reports of verifier set 2.
final   = heldout plus the first 80 other Open-i reports of the train split that are in no labeled set and not in
          data/candidates.jsonl. Nothing was ever trained, so they are unseen by the model; the report must say they come from
          the train split. Every candidate text is cached in results/final_eval_candidates.jsonl so verifier changes only need --rescore.
Systems: `plain` = baseline prompt, greedy; `best_of_n` = verifier pick from 10 structured-prompt candidates plus the plain draft.
Label outputs blind into results/<stem>_labels.csv (item,H,N,F,f) before --score to get labeled error rates.
Verifier metrics are circular for best-of-N (it both selects and scores); labeled errors and readability are not.
"""
import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.agreement import auc  # noqa: E402
from src.bestofn import acceptable, best_of_n, choose, rank  # noqa: E402
from src.data import labeled_ids, load_reports, load_split  # noqa: E402
from src.generate import Generator, build_prompt  # noqa: E402
from src.text import split_sentences  # noqa: E402
from src.verify import Verifier, _fk_grade  # noqa: E402

RES = ROOT / "results"
SYSTEMS = ("plain", "best_of_n")


def heldout_ids() -> list[str]:
    reports, labeled = load_reports(), labeled_ids()
    return sorted(i for i in load_split()["test"] if reports[i]["source"] == "openi" and i not in labeled)


def set2_ids() -> list[str]:
    lines = (RES / "verifier_eval2.jsonl").read_text(encoding="utf-8").splitlines()
    return list(dict.fromkeys(json.loads(line)["report_id"] for line in lines))


def extra_ids(count: int = 80) -> list[str]:
    reports, labeled = load_reports(), labeled_ids()
    used = {str(json.loads(line)["id"]) for line in (ROOT / "data" / "candidates.jsonl").read_text(encoding="utf-8").splitlines()}
    pool = sorted(i for i in load_split()["train"] if reports[i]["source"] == "openi" and i not in labeled and i not in used)
    return pool[:count]


def final_ids() -> list[str]:
    return heldout_ids() + extra_ids()


REPORT_SETS = {"heldout": (heldout_ids, "heldout_eval"), "set2": (set2_ids, "bestofn_eval"),
               "final": (final_ids, "final_eval")}


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def output_rows(rid: str, source: str, plain: str, ranked: list) -> list[dict]:
    best = choose(ranked)
    return [{"system": "plain", "report_id": rid, "source": source, "output": plain},
            {"system": "best_of_n", "report_id": rid, "source": source,
             "output": best.text if best else plain, "n_candidates": len(ranked),
             "acceptable": bool(best and acceptable(best.score)), "fallback": best is None}]


def rescore(key: str):
    """Rebuild <stem>.jsonl from the cached candidates with the current verifier (no generation)."""
    ids, stem = REPORT_SETS[key]
    cache = {r["report_id"]: r for r in read_rows(RES / f"{stem}_candidates.jsonl")}
    reports, verifier, rows = load_reports(), Verifier(), []
    for rid in ids():
        c = cache[rid]
        rows += output_rows(rid, reports[rid]["text"], c["plain"], rank(verifier, reports[rid]["text"], c["texts"]))
    (RES / f"{stem}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(f"rewrote {stem}.jsonl: {len(rows)} rows from {len(cache)} cached reports")


def generate(key: str, n: int, limit: int = 0):
    ids, stem = REPORT_SETS[key]
    ids, path = ids(), RES / f"{stem}.jsonl"
    cache_path = RES / f"{stem}_candidates.jsonl"
    reports = load_reports()
    done = {r["report_id"] for r in read_rows(path)}
    todo = [i for i in ids if i not in done]
    todo = todo[:limit] if limit else todo
    gen, verifier, start = Generator(), Verifier(), time.time()
    for k, rid in enumerate(todo, 1):
        source = reports[rid]["text"]
        plain = gen.generate(build_prompt(source, "baseline"), max_new_tokens=400)[0]
        ranked = best_of_n(gen, verifier, source, n, extra=(plain,), max_new_tokens=400)
        rows = output_rows(rid, source, plain, ranked)
        with cache_path.open("a", encoding="utf-8") as f:      # cache first: a crash here must not lose the generation
            f.write(json.dumps({"report_id": rid, "plain": plain, "texts": [c.text for c in ranked]}) + "\n")
        with path.open("a", encoding="utf-8") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        print(f"[{k}/{len(todo)}] {rid}: {len(ranked)} candidates, acceptable={rows[1]['acceptable']}, "
              f"{(time.time() - start) / k:.0f}s/report", flush=True)


def numbered(stem: str, n_reports: int) -> list[dict]:
    """Rows in a fixed shuffled order; `item` is the blind-labeling number."""
    rows = sorted(read_rows(RES / f"{stem}.jsonl"), key=lambda r: (r["report_id"], r["system"]))
    if len(rows) != 2 * n_reports:
        raise SystemExit(f"{stem}.jsonl has {len(rows)} rows, expected {2 * n_reports}: finish generation first")
    random.Random(5).shuffle(rows)
    seen: dict[tuple[str, str], int] = {}          # a best-of-N output equal to the plain draft shares one label
    for r in rows:
        r["item"] = seen.setdefault((r["report_id"], r["output"]), len(seen))
    return rows


def show(rows: list[dict], start: int, end: int):
    """Blind view: each distinct output once, no system name, no scores."""
    shown = set()
    for r in rows:
        if start <= r["item"] < end and r["item"] not in shown:
            shown.add(r["item"])
            print(f"### ITEM {r['item']}\nSOURCE: {r['source']}\nOUTPUT: {r['output']}\n")


def jaccard(a: str, b: str) -> float:
    x, y = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return len(x & y) / len(x | y)


def boot_ci(diffs: list[float], reps: int = 2000) -> tuple[float, float]:
    rng = random.Random(0)
    means = sorted(sum(rng.choices(diffs, k=len(diffs))) / len(diffs) for _ in range(reps))
    return means[int(0.025 * reps)], means[int(0.975 * reps)]


def score(key: str):
    ids, stem = REPORT_SETS[key]
    rows = numbered(stem, len(ids()))
    verifier = Verifier()
    for r in rows:
        s = verifier.score(r["source"], r["output"])
        r.update(entail=s.entail, numbers=s.numbers, certainty=s.certainty, simplicity=s.simplicity,
                 coverage=s.coverage, total=s.total,
                 passes=float(acceptable(s)), fk=_fk_grade(" ".join(split_sentences(r["output"]))),
                 overlap=jaccard(r["source"], r["output"]))
    by = {s: {r["report_id"]: r for r in rows if r["system"] == s} for s in SYSTEMS}
    rids = sorted(by["plain"])
    labels_path = RES / f"{stem}_labels.csv"
    if labels_path.exists():
        labels = {int(r["item"]): r for r in csv.DictReader(labels_path.open(encoding="utf-8"))}
        for r in rows:
            lab = labels[r["item"]]
            r.update(H=float(lab["H"]), N=float(lab["N"]), F=float(lab["F"]), O=float(lab.get("O") or 0),
                     err=float(any(lab[k] == "1" for k in "HNF")))
    metrics = ["passes", "entail", "numbers", "certainty", "simplicity", "coverage", "total", "fk", "overlap"]
    if labels_path.exists():
        metrics += ["H", "N", "F", "O", "err"]
    names = {"passes": "pass all hard checks", "entail": "meaning (entailment)", "numbers": "numbers/sides",
             "certainty": "certainty", "simplicity": "simplicity", "coverage": "nothing left out (coverage)",
             "total": "verifier total",
             "fk": "reading grade (FK)", "overlap": "word overlap w/ source", "H": "hedge error (labeled)",
             "N": "number/side error (labeled)", "F": "unsupported content (labeled)",
             "O": "key finding left out (labeled)", "err": "any error H/N/F (labeled)"}
    lines = [f"# Plain LLM vs best-of-N ({key}, {len(rids)} reports)", "",
             "| metric | plain LLM | best-of-N | difference (95% CI, paired bootstrap) |", "|---|---|---|---|"]
    for m in metrics:
        a = [by["plain"][i][m] for i in rids]
        b = [by["best_of_n"][i][m] for i in rids]
        lo, hi = boot_ci([y - x for x, y in zip(a, b)])
        lines.append(f"| {names[m]} | {sum(a) / len(a):.2f} | {sum(b) / len(b):.2f} | "
                     f"{(sum(b) - sum(a)) / len(a):+.2f} ({lo:+.2f} to {hi:+.2f}) |")
    if labels_path.exists():
        # the verifier did not pick the plain drafts, so its ability to rank them is not circular
        plain = [by["plain"][i] for i in rids]
        lines += ["", f"## Verifier AUC on the {len(plain)} plain outputs (not circular; 0.5 = chance)", "",
                  "| score vs label | AUC | positives |", "|---|---|---|"]
        for score_key, label_key, text in (("total", "err", "total vs any H/N/F error"), ("certainty", "H", "certainty vs H"),
                                           ("numbers", "N", "numbers vs N"), ("entail", "F", "entail vs F"),
                                           ("coverage", "O", "coverage vs O (omission)")):
            bad = [bool(r[label_key]) for r in plain]
            a = auc([r[score_key] for r in plain], bad)
            lines.append(f"| {text} | {a:.2f} | {sum(bad)} |")
    lines += ["", "Verifier-based rows are circular for best-of-N (the verifier selects and scores). "
              "Labeled rows (if present) were assigned blind by Claude (an AI), not by humans. Reading grade: lower is easier."]
    text = "\n".join(lines) + "\n"
    (RES / f"{stem.replace('_eval', '')}_summary.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", choices=list(REPORT_SETS), default="set2")
    ap.add_argument("--show", nargs=2, type=int, metavar=("START", "END"))
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--rescore", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="generate at most this many new reports (timing test)")
    a = ap.parse_args()
    if a.rescore:
        rescore(a.reports)
    elif a.show:
        stem = REPORT_SETS[a.reports][1]
        show(numbered(stem, len(REPORT_SETS[a.reports][0]())), *a.show)
    elif a.score:
        score(a.reports)
    else:
        generate(a.reports, a.n, a.limit)
