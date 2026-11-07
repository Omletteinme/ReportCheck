"""Write sample report PDFs (text layer, so the demo's upload can read them) to results/review/sample_pdfs/.

    .venv/Scripts/python scripts/make_sample_pdfs.py

Reports come from results/review/sample_inputs*.md (public Open-i reports, plus synthetic ones that are marked as
such inside the PDF). Needs playwright (requirements-figures.txt); it prints through the installed Microsoft Edge.
"""
import re
import sys
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from demo.extract import extract_text  # noqa: E402

SRC = [ROOT / "results" / "review" / "sample_inputs.md", ROOT / "results" / "review" / "sample_inputs_more.md"]
OUT = ROOT / "results" / "review" / "sample_pdfs"
# (id, file label) in the order the files are numbered
PICK = [("10", "normal-chest"), ("3377", "normal-pa-lateral"), ("2522", "possible-effusions"), ("101", "possible-hedge"),
        ("126", "may-represent-pneumonia"), ("1056", "likely-hedge"), ("1339", "measurement"), ("1329", "measurement-2"),
        ("1040", "left-right"), ("1534", "left-right-hedged"), ("1326", "left-right-2"), ("1416", "follow-up"),
        ("1167", "long-many-findings"), ("synth_000", "synthetic-numbers"), ("synth_001", "synthetic-lesion-size")]
BLOCK = re.compile(r"^id: `(?P<id>[^`]+)`.*?\n\n```\n(?P<text>.*?)\n```", re.M | re.S)
PAGE = ("<html><head><meta charset='utf-8'><style>body{{font:14pt/1.55 'Segoe UI',Arial,sans-serif;margin:0;color:#111}}"
        "h1{{font-size:16pt;margin:0 0 14pt}}.note{{margin-top:18pt;font-size:11pt;color:#444}}</style></head><body>"
        "<h1>Radiology report: chest X-ray</h1><p>{body}</p>{note}</body></html>")


def load() -> dict[str, str]:
    reports = {}
    for path in SRC:
        for m in BLOCK.finditer(path.read_text(encoding="utf-8")):
            reports.setdefault(m["id"], m["text"].strip())
    return reports


def main():
    reports = load()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.pdf"):
        old.unlink()
    index = ["# Sample report PDFs for the demo's upload", "",
             "Upload any of these with the Upload file button. Reports are from the public, anonymised Open-i chest X-ray set "
             "(`XXXX` marks text the NLM removed). Files marked synthetic were written by our generator and are not real patients; "
             "the PDF itself says so. Rebuild with `scripts/make_sample_pdfs.py`.", "", "| File | Source | What it tests |", "|---|---|---|"]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page()
        for n, (rid, label) in enumerate(PICK, 1):
            text = reports[rid]
            synth = rid.startswith("synth")
            note = "<div class='note'><b>SYNTHETIC REPORT: not a real patient.</b></div>" if synth else ""
            page.set_content(PAGE.format(body=escape(text), note=note))
            name = f"{n:02d}-{label}.pdf"
            page.pdf(path=str(OUT / name), format="A4", margin={"top": "22mm", "bottom": "20mm", "left": "20mm", "right": "20mm"})
            got = extract_text(name, (OUT / name).read_bytes())
            assert text.split()[0] in got and len(got) > len(text) * 0.9, f"{name}: text layer missing"
            index.append(f"| `{name}` | {'synthetic' if synth else 'Open-i id ' + rid} | {label.replace('-', ' ')} |")
            print("saved", name, flush=True)
        browser.close()
    (OUT / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
