"""Go/no-go statistics for data/{reports,plaba,synthetic}.jsonl. Writes results/data_check.md."""
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("USE_TF", "0")  # global TF install clashes with protobuf

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.patterns import HEDGE_RE, NORMAL_RE, NUMBER_RE, RECOMMEND_RE  # noqa: E402

FILES = {"openi": "reports.jsonl", "plaba": "plaba.jsonl", "synthetic": "synthetic.jsonl"}
OUT = ROOT / "results" / "data_check.md"
TOKENIZER = "Qwen/Qwen2.5-1.5B-Instruct"


def pct(n, total):
    return f"{n} ({100 * n / total:.1f}%)"


def load(name):
    path = ROOT / "data" / FILES[name]
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]


def stats(reports, tok):
    n = len(reports)
    lengths = sorted(len(tok(r["text"]).input_ids) for r in reports)
    s = {"n": n, "median": lengths[n // 2], "p95": lengths[int(n * .95)], "max": lengths[-1]}
    s["fit512"] = sum(l <= 512 for l in lengths)
    s["hedged"] = [r for r in reports if HEDGE_RE.search(r["text"])]
    s["numeric"] = [r for r in reports if NUMBER_RE.search(r["text"])]
    s["both"] = [r for r in s["hedged"] if NUMBER_RE.search(r["text"])]
    s["recommend"] = sum(bool(RECOMMEND_RE.search(r["text"])) for r in reports)
    s["normal"] = sum(bool(NORMAL_RE.search(r["text"])) for r in reports)
    s["anon"] = sum("XXXX" in r["text"] for r in reports)
    s["terms"] = Counter(m.group(0).lower() for r in reports for m in HEDGE_RE.finditer(r["text"]))
    return s


def main():
    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    per = {name: stats(load(name), tok) for name in FILES}

    lines = ["# Data check", "", "Sources: openi = real chest X-ray reports; plaba = PubMed abstracts "
             "(not clinical reports); synthetic = template-generated (must be labeled synthetic in the paper).", "",
             "| source | n | tokens med/p95/max | fit 512 | hedged | numeric | hedge+number | recommend | XXXX |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, s in per.items():
        lines.append(
            f"| {name} | {s['n']} | {s['median']}/{s['p95']}/{s['max']} | {pct(s['fit512'], s['n'])} | "
            f"{pct(len(s['hedged']), s['n'])} | {pct(len(s['numeric']), s['n'])} | "
            f"{pct(len(s['both']), s['n'])} | {pct(s['recommend'], s['n'])} | {pct(s['anon'], s['n'])} |"
        )

    o, p, y = per["openi"], per["plaba"], per["synthetic"]
    hedged = len(o["hedged"]) + len(y["hedged"])
    numeric_clinical = len(o["numeric"]) + len(y["numeric"])
    numeric_all = numeric_clinical + len(p["numeric"])
    lines += [
        "",
        f"openi fully normal (heuristic): {pct(o['normal'], o['n'])}",
        "",
        "## Gate",
        f"- [{'x' if hedged >= 300 else ' '}] >=300 hedged clinical reports, openi+synthetic ({hedged})",
        f"- [{'x' if numeric_clinical >= 150 else ' '}] >=150 numeric clinical reports, openi+synthetic "
        f"({len(o['numeric'])} real + {len(y['numeric'])} synthetic = {numeric_clinical})",
        f"- (info) numeric incl. PLABA abstracts: {numeric_all}",
        f"- [{'x' if o['fit512'] / o['n'] >= .95 else ' '}] >=95% of openi reports fit 512 tokens "
        f"({100 * o['fit512'] / o['n']:.1f}%); PLABA fit: {100 * p['fit512'] / p['n']:.1f}%",
        "- [ ] hedge detector precision >=0.85 on 50 hand-checked sentences (manual)",
        "- [ ] baseline smoke run shows measurable error rate (manual)",
        "",
        "## Hedge term counts (openi)",
        *[f"- {t}: {c}" for t, c in o["terms"].most_common()],
        "",
        "## 10 random hedged openi reports",
    ]
    random.seed(0)
    lines += [f"- **{r['id']}**: {r['text']}" for r in random.sample(o["hedged"], 10)]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:25]))


if __name__ == "__main__":
    main()
