"""Split data/glossary.csv across the team for review -> results/human_labeling/glossary_review.csv.

Each reviewer checks the rows assigned to them: is the plain explanation medically correct and easy to
understand? Fill `ok` with 1/0 and write a better wording in `suggestion` when ok = 0.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM = ["jeevitesh", "harita", "hita", "harshith"]


def main():
    rows = list(csv.DictReader((ROOT / "data" / "glossary.csv").open(encoding="utf-8")))
    out = ROOT / "results" / "human_labeling" / "glossary_review.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["assigned_to", "term", "plain_explanation", "ok_1_or_0", "suggestion"])
        for i, r in enumerate(rows):
            w.writerow([TEAM[i % len(TEAM)], r["term"], r["plain"], "", ""])
    print(f"{len(rows)} terms split across {len(TEAM)} reviewers -> {out}")


if __name__ == "__main__":
    main()
