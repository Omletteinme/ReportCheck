"""Check a small LLM runs on this GPU: load, generate, report VRAM and speed.

Usage: python scripts/vram_test.py [model_id]
"""
import os
import sys
import time

os.environ.setdefault("USE_TF", "0")  # global TF install clashes with protobuf

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen2.5-1.5B-Instruct"

REPORT = (
    "FINDINGS: There is a 6 mm nodular opacity in the right lower lobe. "
    "The cardiac silhouette is mildly enlarged. No pleural effusion. "
    "IMPRESSION: Right lower lobe nodule, possibly infectious, though neoplasm "
    "cannot be excluded. Recommend follow-up CT in 3 months."
)
PROMPT = (
    "Rewrite this radiology report in plain language for a patient. Keep every "
    "number and keep the same level of certainty.\n\n" + REPORT
)


def gb(x):
    return x / 1024**3


tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16).cuda()
print(f"loaded {MODEL}: {gb(torch.cuda.memory_allocated()):.2f} GB allocated")

msgs = [{"role": "user", "content": PROMPT}]
ids = tok.apply_chat_template(
    msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True
).to("cuda")

torch.cuda.reset_peak_memory_stats()
t0 = time.time()
out = model.generate(**ids, max_new_tokens=200, do_sample=False)
dt = time.time() - t0
n_in = ids["input_ids"].shape[1]
n = out.shape[1] - n_in
print(f"generated {n} tokens in {dt:.1f}s ({n / dt:.1f} tok/s)")
print(f"peak VRAM during generate: {gb(torch.cuda.max_memory_allocated()):.2f} GB")
print("\n--- output ---\n" + tok.decode(out[0, n_in:], skip_special_tokens=True))
