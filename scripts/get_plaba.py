"""Convert PLABA (Attal et al., 2023; https://osf.io/rnpmf/) into data/plaba.jsonl.

Expects data/raw/plaba/data.json. One record per abstract; `reference` holds the
first expert plain-language adaptation (sentence order preserved), used only as
an optional sanity-check/SFT reference, never as the training objective.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "plaba" / "data.json"
OUT = ROOT / "data" / "plaba.jsonl"


def join(sentences: dict) -> str:
    return " ".join(sentences[k].strip() for k in sorted(sentences, key=int) if sentences[k].strip())


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    records = []
    for qid, q in data.items():
        for pmid, doc in q.items():
            if pmid in ("question", "question_type"):
                continue
            adaptations = doc.get("adaptations", {})
            reference = join(adaptations[sorted(adaptations)[0]]) if adaptations else ""
            records.append(
                {
                    "id": f"plaba_{pmid}",
                    "source": "plaba",
                    "title": doc.get("Title", ""),
                    "text": join(doc["abstract"]),
                    "reference": reference,
                }
            )
    OUT.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} abstracts to {OUT}")


if __name__ == "__main__":
    main()
