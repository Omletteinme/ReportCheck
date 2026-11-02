"""Score the team's labels: agreement with each other and with Claude, and the verifier against human labels.

Put each completed sheet (CSV, same columns as results/human_labeling/sheets/*.csv) into
results/human_labeling/filled/. Needs at least 2 sheets. Majority label = at least half of the humans say 1.
Writes results/human_labeling/report.md.
"""
import csv
import math
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.agreement import auc, cohen_kappa, majority  # noqa: E402

DIR = ROOT / "results" / "human_labeling"
COLS = {"H": "H_certainty_changed", "N": "N_number_or_side_wrong", "F": "F_unsupported_content"}


def read_sheet(path: Path) -> dict[str, dict]:
    rows = {}
    for r in csv.DictReader(path.open(encoding="utf-8-sig")):
        vals = {k: r[c].strip() for k, c in COLS.items()}
        bad = [k for k, v in vals.items() if v not in ("0", "1")]
        if bad:
            raise SystemExit(f"{path.name}: row {r['id']} has blank/invalid {bad}; every cell must be 0 or 1")
        rows[r["id"]] = {"source": r["clinical_report"], "output": r["patient_version"],
                         **{k: int(v) for k, v in vals.items()}}
    return rows


def fmt(x: float) -> str:
    return "n/a" if math.isnan(x) else f"{x:.2f}"


def main():
    sheets = {p.stem: read_sheet(p) for p in sorted((DIR / "filled").glob("*.csv"))}
    if len(sheets) < 2:
        raise SystemExit("need at least 2 completed sheets in results/human_labeling/filled/")
    key = {r["id"]: r for r in csv.DictReader((DIR / "claude_key.csv").open(encoding="utf-8"))}
    ids = sorted(key)
    for name, rows in sheets.items():
        if set(rows) != set(ids):
            raise SystemExit(f"{name}: item ids do not match the key (did you edit the first column?)")

    def col(rows, k):
        return [rows[i][k] for i in ids]

    def anyerr(rows):
        return [int(any(rows[i][k] for k in "HNF")) for i in ids]

    claude = {k: [int(key[i][k]) for i in ids] for k in "HNF"}
    claude["any"] = [int(any(claude[k][j] for k in "HNF")) for j in range(len(ids))]
    human = {name: {**{k: col(rows, k) for k in "HNF"}, "any": anyerr(rows)} for name, rows in sheets.items()}
    out = [f"# Human labeling report ({len(sheets)} labelers, {len(ids)} items)", ""]

    out += ["## Agreement (Cohen's kappa; 1 = perfect, 0 = chance, n/a = a label never varies)", "",
            "| label | positives (Claude) | human-human mean kappa | each human vs Claude |", "|---|---|---|---|"]
    for k in ("H", "N", "F", "any"):
        pair = [cohen_kappa(human[a][k], human[b][k]) for a, b in combinations(human, 2)]
        pair = [x for x in pair if not math.isnan(x)]
        vs = ", ".join(f"{n}: {fmt(cohen_kappa(h[k], claude[k]))}" for n, h in human.items())
        out.append(f"| {k} | {sum(claude[k])} | {fmt(sum(pair) / len(pair)) if pair else 'n/a'} | {vs} |")

    maj = {k: majority([h[k] for h in human.values()]) for k in ("H", "N", "F", "any")}
    out += ["", f"Majority-vs-Claude kappa: " + ", ".join(f"{k} {fmt(cohen_kappa(maj[k], claude[k]))}" for k in maj),
            "", "## Verifier against human majority labels", ""]
    from src.verify import Verifier

    verifier = Verifier()
    first = next(iter(sheets.values()))
    scores = [verifier.score(first[i]["source"], first[i]["output"]) for i in ids]
    for label, bad in (("any error, human majority", maj["any"]), ("any error, Claude", claude["any"])):
        out.append(f"- AUC of verifier total vs {label}: {fmt(auc([s.total for s in scores], [bool(b) for b in bad]))}")
    out.append(f"- AUC certainty vs H (human majority): {fmt(auc([s.certainty for s in scores], [bool(b) for b in maj['H']]))}")
    out.append(f"- AUC entailment vs F (human majority): {fmt(auc([s.entail for s in scores], [bool(b) for b in maj['F']]))}")
    (DIR / "report.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
