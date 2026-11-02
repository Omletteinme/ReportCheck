"""Baseline smoke run: simplify 20 hedged reports with a plain prompt.

Writes results/smoke_baseline.md for manual labeling. For each report mark:
numbers kept? / hedge level kept? / anything added that is not in the source?

Usage: python scripts/smoke_baseline.py [openi|synthetic] [model_id]

synthetic mode also checks automatically that every ground-truth number in
`meta` survives into the output (numeric value match; units may be reworded).
"""
import json
import os
import random
import re
import sys
from pathlib import Path

os.environ.setdefault("USE_TF", "0")  # global TF install clashes with protobuf

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.patterns import HEDGE_RE  # noqa: E402

SOURCE = sys.argv[1] if len(sys.argv) > 1 else "openi"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "Qwen/Qwen2.5-1.5B-Instruct"
PROMPT = (
    "Rewrite this radiology report in plain language for a patient. Keep every "
    "number and keep the same level of certainty. Do not add anything not in the report.\n\n"
)
N = 20


def has_value(text, number):
    """True if the numeric value of e.g. '6 mm' appears in text (units may be reworded)."""
    value = re.match(r"[\d.]+", number).group()
    return re.search(r"(?<![\d.])" + re.escape(value) + r"(?!\d)", text) is not None


def main():
    path_in = ROOT / "data" / ("synthetic.jsonl" if SOURCE == "synthetic" else "reports.jsonl")
    reports = [json.loads(l) for l in path_in.read_text(encoding="utf-8").splitlines()]
    hedged = [r for r in reports if HEDGE_RE.search(r["text"])]
    random.seed(1)
    sample = random.sample(hedged, N)
    kept = total = 0

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16).cuda()

    out = ["# Baseline smoke run", "", "Label each: numbers kept [ ]  hedge kept [ ]  hallucination [ ]", ""]
    for r in sample:
        ids = tok.apply_chat_template(
            [{"role": "user", "content": PROMPT + r["text"]}], add_generation_prompt=True,
            return_tensors="pt", return_dict=True,
        ).to("cuda")
        gen = model.generate(**ids, max_new_tokens=250, do_sample=False)
        text = tok.decode(gen[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)
        if SOURCE == "synthetic":
            miss = [x for x in r["meta"]["numbers"] if not has_value(text, x)]
            kept += len(r["meta"]["numbers"]) - len(miss)
            total += len(r["meta"]["numbers"])
        out += [f"## {r['id']}", f"**Source:** {r['text']}", "", f"**Output:** {text}", ""]
        if SOURCE == "synthetic":
            out.append(f"_auto: missing numbers {miss}_")
        out += ["- numbers kept: ?  hedge kept: ?  hallucination: ?", ""]
        print("done", r["id"])
    if SOURCE == "synthetic":
        out.insert(2, f"**Auto number retention: {kept}/{total} ({100 * kept / total:.0f}%)**\n")
    path = ROOT / "results" / ("smoke_synthetic.md" if SOURCE == "synthetic" else "smoke_baseline.md")
    path.write_text("\n".join(out), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
