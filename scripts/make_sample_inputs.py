"""Build results/review/sample_inputs_more.md: ~40 demo inputs grouped by what they exercise.

Real reports come only from the held-out test split (data/split.json); SYNTHETIC ones are marked as such.
Selection is deterministic (sorted ids, no randomness), so rerunning gives the same file.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.discourse import parse_report  # noqa: E402
from src.numbers import sides  # noqa: E402

PER_GROUP = 4
MAX_WORDS = 140


def load(name):
    return [json.loads(line) for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def features(text):
    rep = parse_report(text)
    nums = [n for u in rep.units for n in u.numbers if n[1] != "month"]
    return {
        "numbers": len(nums),
        "hedged": {u.certainty for u in rep.units} - {"definite"},
        "recommend": any(u.role == "recommendation" for u in rep.units),
        "sides": sides(text),
        "sentences": len(rep.units),
        "words": len(text.split()),
    }


GROUPS = [
    ("Normal study (nothing to explain)", lambda f, t: f["sentences"] >= 3 and not f["hedged"] and not f["numbers"]
     and "no acute" in t.lower()),
    ("'Possible' / 'cannot be excluded' hedges", lambda f, t: "possible" in f["hedged"]),
    ("'Likely' / 'consistent with' hedges", lambda f, t: "likely" in f["hedged"] and "possible" not in f["hedged"]),
    ("'Unlikely' hedges", lambda f, t: "unlikely" in f["hedged"]),
    ("Measurements that must survive", lambda f, t: f["numbers"] >= 2),
    ("Left and right both mentioned", lambda f, t: f["sides"] == {"left", "right"} and "bilateral" not in t.lower()),
    ("Follow-up recommended", lambda f, t: f["recommend"] and f["hedged"]),
    ("Short and simple", lambda f, t: f["words"] <= 35 and f["sentences"] >= 2),
    ("Long, many findings", lambda f, t: f["sentences"] >= 9 and f["words"] <= MAX_WORDS + 40),
]


def block(row, source_label):
    text = " ".join(row["text"].split())
    return f"id: `{row['id']}`  ({source_label})\n\n```\n{text}\n```\n"


def main():
    split = json.loads((ROOT / "data" / "split.json").read_text(encoding="utf-8"))
    test_ids = set(split["test"])
    real = sorted((r for r in load("reports.jsonl") if str(r["id"]) in test_ids and len(r["text"].split()) <= MAX_WORDS + 40),
                  key=lambda r: str(r["id"]))
    used, out = set(), [
        "# More sample inputs for the demo",
        "",
        "Real reports are from the public Open-i chest X-ray collection and come only from the held-out test split. "
        "Reports marked SYNTHETIC were written by our generator and are not real patients. "
        "Rebuild with `scripts/make_sample_inputs.py`.",
        "",
    ]
    for title, test in GROUPS:
        picks = []
        for r in real:
            if r["id"] in used:
                continue
            f = features(r["text"])
            if test(f, r["text"]):
                picks.append(r)
                used.add(r["id"])
            if len(picks) == PER_GROUP:
                break
        if picks:
            out += [f"## {title}", ""] + [block(r, "real, Open-i") for r in picks]
        print(f"{title}: {len(picks)}")

    synth = [r for r in load("synthetic.jsonl")]
    dense = sorted(synth, key=lambda r: -len(r["meta"]["numbers"]))[:PER_GROUP]
    out += ["## Number-dense (SYNTHETIC, not real patients)", ""] + [block(r, "SYNTHETIC") for r in dense]
    unlikely = [r for r in synth if r["meta"]["certainty"] == "unlikely"][:2]
    out += ["## Negated-diagnosis wording (SYNTHETIC, not real patients)", ""] + [block(r, "SYNTHETIC") for r in unlikely]

    dest = ROOT / "results" / "review" / "sample_inputs_more.md"
    dest.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {dest} ({sum(1 for line in out if line.startswith('id: '))} inputs)")


if __name__ == "__main__":
    main()
