"""Sanity-check the verifier against the 20 labeled baseline outputs.

Reads results/smoke_baseline.md (source + output) and results/smoke_baseline_labels.md
(error labels), scores each output, and reports how well the total separates clean
outputs from outputs with a labeled hedge/number/fabrication error (pairwise AUC).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.verify import Verifier  # noqa: E402


def load_pairs():
    pairs = {}
    for block in (ROOT / "results" / "smoke_baseline.md").read_text(encoding="utf-8").split("\n## ")[1:]:
        rid = block.split("\n")[0].strip()
        src = re.search(r"\*\*Source:\*\* (.*?)\n", block).group(1)
        out = block.split("**Output:**")[1].split("\n- numbers kept")[0].strip()
        pairs[rid] = (src, out)
    return pairs


def load_labels():
    labels = {}
    for line in (ROOT / "results" / "smoke_baseline_labels.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 4 and cells[0].isdigit():
            labels[cells[0]] = {"H": cells[1] == "H", "N": cells[2] == "N", "F": cells[3] == "F", "f": cells[3] == "f"}
    return labels


def main():
    pairs, labels, v = load_pairs(), load_labels(), Verifier()
    rows = []
    for rid, (src, out) in pairs.items():
        s = v.score(src, out)
        lab = labels[rid]
        bad = lab["H"] or lab["N"] or lab["F"]
        rows.append((rid, bad, s))
        flags = "".join(k for k in "HNF" if lab[k]) or "-"
        print(f"{rid:>5} {flags:>3}  total={s.total:.2f} ent={s.entail:.2f} num={s.numbers:.2f} "
              f"cert={s.certainty:.2f} simp={s.simplicity:.2f}")
    good = [s.total for _, bad, s in rows if not bad]
    bad = [s.total for _, bad, s in rows if bad]
    auc = sum((g > b) + 0.5 * (g == b) for g in good for b in bad) / (len(good) * len(bad))
    print(f"\nclean n={len(good)} mean={sum(good) / len(good):.3f} | "
          f"errored n={len(bad)} mean={sum(bad) / len(bad):.3f} | pairwise AUC={auc:.2f}")


if __name__ == "__main__":
    main()
