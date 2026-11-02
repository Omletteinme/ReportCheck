"""Which medical terms do the reports use, and does data/glossary.csv cover them?

Prints (1) the most frequent long words and two-word phrases NOT yet in the glossary, so gaps are chosen from
data, and (2) the share of reports containing at least one glossary term.
Usage: python scripts/glossary_coverage.py [--top 120]
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data import load_reports  # noqa: E402

STOP = set("""there which within without these those their about other between because seen noted consistent
compatible normal findings impression otherwise appears appearance changes change evidence stable unchanged
comparison previous interval prior limits redemonstration identified present visualized demonstrated
bilateral""".split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=120)
    top = ap.parse_args().top
    texts = [r["text"].lower() for r in load_reports().values() if r["source"] == "openi"]
    covered: set[str] = set()
    try:
        from src.glossary import load

        covered = {t for entry in load() for t in [entry["term"], *entry["variants"]]}
    except (ImportError, FileNotFoundError):
        pass
    words, pairs = Counter(), Counter()
    for t in texts:
        tokens = re.findall(r"[a-z]{4,}", t)
        words.update(set(w for w in tokens if len(w) >= 8 and w not in STOP and w != "xxxx"))
        pairs.update(set(f"{a} {b}" for a, b in zip(tokens, tokens[1:])))
    print(f"{len(texts)} Open-i reports; {len(covered)} glossary terms/variants loaded\n")
    print("Frequent long words not in glossary (reports containing the word):")
    print(", ".join(f"{w} {c}" for w, c in words.most_common(top) if w not in covered))
    print("\nFrequent two-word phrases containing a long word, not in glossary:")
    long_pairs = [(p, c) for p, c in pairs.most_common(400) if any(len(w) >= 8 for w in p.split()) and p not in covered]
    print(", ".join(f"{p} {c}" for p, c in long_pairs[:top]))
    if covered:
        pattern = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in sorted(covered, key=len, reverse=True)) + r")\b")
        hit = sum(bool(pattern.search(t)) for t in texts)
        print(f"\nReports with at least one glossary term: {hit}/{len(texts)} ({100 * hit / len(texts):.0f}%)")


if __name__ == "__main__":
    main()
