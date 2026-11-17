"""Blind AI labeling of the rule-based and T5-hybrid outputs on the 120 evaluation reports.

    .venv/Scripts/python scripts/t5_labeling.py make [--chunks 3]    # build the blind sheets
    .venv/Scripts/python scripts/t5_labeling.py score                # merge the labels, compare the systems

make:  results/t5_label_sheets/chunk_K.md hold ITEM / SOURCE / OUTPUT only (no system, no score) for every distinct output of
       the `rules` and `hybrid_guard` systems plus CONTROLS already-labeled earlier items, shuffled together, so the labeler
       cannot tell which system wrote what and its consistency can be measured. The key results/t5_label_key.jsonl maps items to
       systems: never show it to a labeler. It is committed now that labeling is finished, so the scoring can be rerun.
score: reads results/t5_label_sheets/chunk_K_labels.csv (item,H,N,F,f,O), writes results/t5_label_summary.md.
All labels are assigned by Claude (an AI) under results/human_labeling/GUIDELINES.md, not by humans.
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from src.agreement import cohen_kappa  # noqa: E402

import eval_bestofn  # noqa: E402

RES = ROOT / "results"
SHEETS = RES / "t5_label_sheets"
KEY = RES / "t5_label_key.jsonl"
NEW_SYSTEMS = ("rules", "hybrid_guard")
FIRST_ITEM, CONTROLS, SEED = 1000, 30, 7
KINDS = "HNFfO"


def old_labels() -> tuple[dict, dict]:
    """({(report_id, output): label row}, {(report_id, system): (report_id, output)}) from the earlier final evaluation."""
    rows = eval_bestofn.numbered("final_eval", 120)
    labels = {int(r["item"]): r for r in csv.DictReader((RES / "final_eval_labels.csv").open(encoding="utf-8"))}
    by_text, by_system = {}, {}
    for r in rows:
        by_text[(r["report_id"], r["output"])] = {"item": r["item"], "source": r["source"], **labels[r["item"]]}
        by_system[(r["report_id"], r["system"])] = (r["report_id"], r["output"])
    return by_text, by_system


def make(chunks: int):
    new_rows = [json.loads(line) for line in (RES / "t5_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    sources = {r["report_id"]: r["source"] for r in eval_bestofn.read_rows(RES / "final_eval.jsonl")}
    by_text, _ = old_labels()
    distinct: dict[tuple[str, str], dict] = {}
    for r in new_rows:
        if r["system"] in NEW_SYSTEMS:
            entry = distinct.setdefault((r["report_id"], r["text"]), {"report_id": r["report_id"], "source": sources[r["report_id"]],
                                                                      "output": r["text"], "systems": [], "kind": "new"})
            entry["systems"].append(r["system"])
    reused = [k for k in distinct if k in by_text]
    for k in reused:                                   # an output identical to an already-labeled one keeps that label
        distinct.pop(k)
    rng = random.Random(SEED)
    controls = [{"report_id": rid, "source": v["source"], "output": out, "systems": [], "kind": "control", "old_item": v["item"],
                 "old": {k: v[k] for k in KINDS if k in v}}
                for (rid, out), v in rng.sample(sorted(by_text.items()), CONTROLS)]
    items = list(distinct.values()) + controls
    rng.shuffle(items)
    for n, it in enumerate(items):
        it["item"] = FIRST_ITEM + n
    KEY.write_text("".join(json.dumps(it) + "\n" for it in items), encoding="utf-8")
    SHEETS.mkdir(exist_ok=True)
    for old in SHEETS.glob("chunk_*.md"):
        old.unlink()
    size = -(-len(items) // chunks)
    for k in range(chunks):
        part = items[k * size:(k + 1) * size]
        (SHEETS / f"chunk_{k + 1}.md").write_text(
            "".join(f"### ITEM {it['item']}\nSOURCE: {it['source']}\nOUTPUT: {it['output']}\n\n" for it in part), encoding="utf-8")
        print(f"chunk_{k + 1}.md: items {part[0]['item']}-{part[-1]['item']} ({len(part)})")
    print(f"{len(distinct)} new distinct outputs ({len(reused)} reused an earlier label) + {len(controls)} controls = {len(items)} items")


def boot_ci(diffs, reps=2000):
    rng = random.Random(0)
    means = sorted(sum(rng.choices(diffs, k=len(diffs))) / len(diffs) for _ in range(reps))
    return means[int(0.025 * reps)], means[int(0.975 * reps)]


def label_table(systems=("plain", "best_of_n", "rules", "hybrid_guard")):
    """({system: {report_id: {H, N, F, f, O, err}}}, report ids, key items, new labels by item) from the merged labels."""
    items = [json.loads(line) for line in KEY.read_text(encoding="utf-8").splitlines()]
    new = {}
    for path in sorted(SHEETS.glob("chunk_*_labels.csv")):
        for r in csv.DictReader(path.open(encoding="utf-8")):
            new[int(r["item"])] = r
    missing = [it["item"] for it in items if it["item"] not in new]
    if missing:
        raise SystemExit(f"{len(missing)} items have no label yet, for example {missing[:5]}")
    by_text, by_system = old_labels()
    label_of = {(it["report_id"], it["output"]): new[it["item"]] for it in items if it["kind"] == "new"}
    label_of.update({k: v for k, v in by_text.items() if k not in label_of})
    new_rows = [json.loads(line) for line in (RES / "t5_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    text_of = {(r["report_id"], r["system"]): r["text"] for r in new_rows}
    ids = sorted({rid for rid, _ in text_of})

    def lab(rid, system):
        key = by_system[(rid, system)] if system in ("plain", "best_of_n") else (rid, text_of[(rid, system)])
        row = label_of[key]
        flags = {k: int(row.get(k) or 0) for k in KINDS}
        flags["err"] = int(any(flags[k] for k in "HNF"))
        return flags

    return {s: {rid: lab(rid, s) for rid in ids} for s in systems}, ids, items, new


def score():
    systems = ("plain", "best_of_n", "rules", "hybrid_guard")
    table, ids, items, new = label_table(systems)
    names = {"err": "any error (H, N or F)", "F": "unsupported or wrong content (F)", "H": "hedge level changed (H)",
             "N": "number or side wrong (N)", "O": "key finding left out (O)", "f": "minor gloss slip only (f, not an error)"}
    lines = [f"# Labeled error rates, {len(ids)} reports (labels assigned blind by Claude, an AI, not by humans)", "",
             "| error | " + " | ".join(systems) + " | hybrid_guard minus plain (95% CI) | hybrid_guard minus best_of_n (95% CI) |",
             "|---|" + "---|" * (len(systems) + 2)]
    for k, name in names.items():
        means = [sum(table[s][i][k] for i in ids) / len(ids) for s in systems]
        cells = []
        for base in ("plain", "best_of_n"):
            diffs = [table["hybrid_guard"][i][k] - table[base][i][k] for i in ids]
            lo, hi = boot_ci(diffs)
            cells.append(f"{sum(diffs) / len(ids):+.2f} ({lo:+.2f} to {hi:+.2f})")
        lines.append(f"| {name} | " + " | ".join(f"{m:.2f}" for m in means) + f" | {cells[0]} | {cells[1]} |")
    controls = [it for it in items if it["kind"] == "control"]
    lines += ["", f"## Labeler consistency on {len(controls)} control items (the same outputs labeled earlier and again here)", "",
              "| label | agreement | Cohen's kappa |", "|---|---|---|"]
    for k in "HNFO":
        a = [int(it["old"].get(k) or 0) for it in controls]
        b = [int(new[it["item"]].get(k) or 0) for it in controls]
        lines.append(f"| {k} | {sum(x == y for x, y in zip(a, b)) / len(a):.0%} | {cohen_kappa(a, b):.2f} |")
    lines += ["", "Treat these as AI-labeled, exploratory numbers: one labeler, no clinician, and the control items show how stable it is."]
    text = "\n".join(lines) + "\n"
    (RES / "t5_label_summary.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["make", "score"])
    ap.add_argument("--chunks", type=int, default=3)
    a = ap.parse_args()
    make(a.chunks) if a.command == "make" else score()
