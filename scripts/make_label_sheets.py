"""Build blind labeling sheets for the team from the Claude-labeled verifier sets.

36 outputs = 12 from each of verifier sets 1, 2 and 3 (6 clean + 6 errored per Claude's labels, so sheets are
not 85% errors). Each annotator gets the same items in a different random order; prompt mode and Claude's
labels are hidden. Claude's labels go to results/human_labeling/claude_key.csv (do NOT share that file).
"""
import csv
import json
import random
from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "results"
OUT = RES / "human_labeling"
ANNOTATORS = ["jeevitesh", "harita", "hita", "harshith"]
SETS = {"1": "verifier_eval", "2": "verifier_eval2", "3": "verifier_eval3"}


def load(set_id: str) -> list[dict]:
    stem = SETS[set_id]
    labels = {int(r["item"]): r for r in csv.DictReader((RES / f"{stem}_labels.csv").open(encoding="utf-8"))}
    rows = []
    for line in (RES / f"{stem}.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        lab = labels[r["item"]]
        rows.append({"set": set_id, "orig_item": r["item"], "source": r["source"], "output": r["output"],
                     "H": int(lab["H"]), "N": int(lab["N"]), "F": int(lab["F"])})
    return rows


def main():
    rng = random.Random(21)
    chosen = []
    for set_id in SETS:
        rows = load(set_id)
        clean = [r for r in rows if not (r["H"] or r["N"] or r["F"])]
        bad = [r for r in rows if r["H"] or r["N"] or r["F"]]
        chosen += rng.sample(clean, 6) + rng.sample(bad, 6)
    rng.shuffle(chosen)
    for i, r in enumerate(chosen):
        r["id"] = f"L{i:02d}"

    (OUT / "sheets").mkdir(parents=True, exist_ok=True)
    for name in ANNOTATORS:
        order = chosen[:]
        random.Random(name).shuffle(order)
        with (OUT / "sheets" / f"{name}.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["id", "clinical_report", "patient_version", "H_certainty_changed", "N_number_or_side_wrong",
                        "F_unsupported_content", "notes"])
            w.writerows([[r["id"], r["source"], r["output"], "", "", "", ""] for r in order])
    with (OUT / "claude_key.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "set", "orig_item", "H", "N", "F"])
        w.writerows([[r["id"], r["set"], r["orig_item"], r["H"], r["N"], r["F"]] for r in chosen])
    print(f"{len(chosen)} items; sheets for {', '.join(ANNOTATORS)} in {OUT / 'sheets'}")


if __name__ == "__main__":
    main()
