"""Generate 50 SYNTHETIC number-dense radiology reports -> data/synthetic.jsonl.

Every record has source="synthetic" and must be reported as such in the paper.
Reports are template-built (seeded, deterministic) in the Open-i FINDINGS/IMPRESSION
style. Each record carries ground truth in `meta` (numbers, certainty level, whether
a follow-up is recommended) so the verifier and QA set can be checked against it.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "synthetic.jsonl"
N = 50

# (hedge phrase used in the report, certainty level)
HEDGES = [
    ("is likely", "likely"),
    ("may represent", "possible"),
    ("is suspicious for", "likely"),
    ("cannot be excluded", "possible"),
    ("is unlikely to represent", "unlikely"),
    ("is consistent with", "likely"),
    ("could represent", "possible"),
    ("is definitely", "definite"),
]
LOBES = ["right upper lobe", "right middle lobe", "right lower lobe",
         "left upper lobe", "left lower lobe", "lingula"]
ORGANS = [
    ("liver", "hepatic lesion", ["a hemangioma", "a metastasis", "a simple cyst"]),
    ("kidney", "renal lesion", ["a simple cyst", "a renal cell carcinoma", "an angiomyolipoma"]),
    ("thyroid", "thyroid nodule", ["a benign colloid nodule", "a papillary carcinoma"]),
    ("adrenal gland", "adrenal nodule", ["an adenoma", "a metastasis"]),
]
FOLLOWUP = [
    ("Recommend follow-up CT in {m} months.", True),
    ("Recommend repeat imaging in {m} months.", True),
    ("Clinical correlation is advised.", True),
    ("No follow-up imaging is needed.", False),
]


def lung_nodule(rng):
    size, prior = rng.randint(4, 28), rng.randint(3, 24)
    lobe = rng.choice(LOBES)
    hedge, level = rng.choice(HEDGES)
    dx = rng.choice(["infection", "a primary lung neoplasm", "a granuloma", "a metastasis"])
    follow, rec = rng.choice(FOLLOWUP)
    months = rng.choice([3, 6, 12])
    findings = (
        f"There is a {size} mm nodule in the {lobe}, previously {prior} mm. "
        f"No pleural effusion. The heart measures {rng.randint(11, 16)} cm in transverse diameter."
    )
    impression = f"{lobe.capitalize()} nodule that {hedge} {dx}. {follow.format(m=months)}"
    return findings, impression, {
        "numbers": [f"{size} mm", f"{prior} mm"], "certainty": level, "followup": rec,
    }


def organ_lesion(rng):
    organ, name, dxs = rng.choice(ORGANS)
    size = round(rng.uniform(0.8, 6.5), 1)
    hu = rng.randint(5, 85)
    hedge, level = rng.choice(HEDGES)
    dx = rng.choice(dxs)
    follow, rec = rng.choice(FOLLOWUP)
    months = rng.choice([3, 6, 12])
    findings = (
        f"A {size} cm {name} is seen in the {organ}, measuring {hu} Hounsfield units. "
        f"The remaining {organ} is unremarkable."
    )
    impression = f"{name.capitalize()} that {hedge} {dx}. {follow.format(m=months)}"
    return findings, impression, {
        "numbers": [f"{size} cm", f"{hu} Hounsfield units"], "certainty": level, "followup": rec,
    }


def lab_style(rng):
    ef = rng.randint(25, 65)
    stenosis = rng.choice([30, 50, 70, 90])
    hedge, level = rng.choice(HEDGES[:7])
    follow, rec = rng.choice(FOLLOWUP)
    months = rng.choice([3, 6, 12])
    findings = (
        f"Left ventricular ejection fraction is {ef}%. "
        f"There is {stenosis}% narrowing of the proximal left anterior descending artery."
    )
    impression = (
        f"Narrowing of the left anterior descending artery that {hedge} a hemodynamically "
        f"significant stenosis. {follow.format(m=months)}"
    )
    return findings, impression, {
        "numbers": [f"{ef}%", f"{stenosis}%"], "certainty": level, "followup": rec,
    }


def main():
    rng = random.Random(42)
    builders = [lung_nodule, organ_lesion, lab_style]
    records = []
    for i in range(N):
        findings, impression, meta = builders[i % len(builders)](rng)
        records.append(
            {
                "id": f"synth_{i:03d}",
                "source": "synthetic",
                "findings": findings,
                "impression": impression,
                "text": f"FINDINGS: {findings} IMPRESSION: {impression}",
                "meta": meta,
            }
        )
    OUT.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} SYNTHETIC reports to {OUT}")
    print(records[0]["text"])


if __name__ == "__main__":
    main()
