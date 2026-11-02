"""Parse Open-i / IU X-ray report XMLs into data/reports.jsonl.

Expects the archive extracted at data/raw/openi_xml (see README). One record
per report with non-empty findings or impression; exact-text duplicates dropped.
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XML_DIR = ROOT / "data" / "raw" / "openi_xml"
OUT = ROOT / "data" / "reports.jsonl"


def section(root, label):
    for el in root.iter("AbstractText"):
        if el.get("Label") == label:
            return re.sub(r"\s+", " ", (el.text or "")).strip()
    return ""


def main():
    records, seen = [], set()
    for path in sorted(XML_DIR.rglob("*.xml")):
        root = ET.parse(path).getroot()
        findings, impression = section(root, "FINDINGS"), section(root, "IMPRESSION")
        if not (findings or impression):
            continue
        text = f"FINDINGS: {findings} IMPRESSION: {impression}".strip()
        if text in seen:
            continue
        seen.add(text)
        records.append(
            {"id": path.stem, "source": "openi", "findings": findings, "impression": impression, "text": text}
        )
    OUT.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} reports to {OUT}")


if __name__ == "__main__":
    main()
