"""Fine-tune t5-base on the sentence pairs from scripts/prep_t5_data.py.

    .venv/Scripts/python scripts/train_t5.py [--epochs 6]

Saves the checkpoint with the lowest validation loss to models/t5-lay/ (ignored by git). Needs the GPU: close games first.
Note: validation reports are separate from training reports, but stock sentences recur across reports, so validation
loss is optimistic about unseen phrasing.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.t5gen import MODEL_DIR, PREFIX  # noqa: E402

BASE = "t5-base"
DATA = ROOT / "data" / "raw" / "t5"


def read(name: str) -> list[dict]:
    return [json.loads(line) for line in (DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]


def batches(rows, tok, size, shuffle):
    rows = list(rows)
    if shuffle:
        random.shuffle(rows)
    for i in range(0, len(rows), size):
        part = rows[i:i + size]
        x = tok([PREFIX + r["source"] for r in part], return_tensors="pt", padding=True, truncation=True, max_length=128)
        y = tok([r["target"] for r in part], return_tensors="pt", padding=True, truncation=True, max_length=128).input_ids
        y[y == tok.pad_token_id] = -100
        yield x.to("cuda"), y.to("cuda")


def evaluate(model, rows, tok) -> float:
    model.eval()
    total, count = 0.0, 0
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for x, y in batches(rows, tok, 32, False):
            n = int((y != -100).sum())
            total += model(**x, labels=y).loss.item() * n
            count += n
    return total / count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()
    random.seed(0)
    torch.manual_seed(0)
    train, val = read("train"), read("val")
    print(f"train {len(train)} pairs, validation {len(val)} pairs", flush=True)
    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSeq2SeqLM.from_pretrained(BASE).cuda()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = args.epochs * ((len(train) + args.batch - 1) // args.batch)
    sched = get_linear_schedule_with_warmup(opt, int(0.05 * steps), steps)
    best, start = float("inf"), time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        running, n = 0.0, 0
        for x, y in batches(train, tok, args.batch, True):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = model(**x, labels=y).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            running += loss.item(); n += 1
        val_loss = evaluate(model, val, tok)
        saved = val_loss < best
        if saved:
            best = val_loss
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(MODEL_DIR)
            tok.save_pretrained(MODEL_DIR)
        print(f"epoch {epoch}/{args.epochs}: train loss {running / n:.3f}, validation loss {val_loss:.3f}"
              f"{' (saved)' if saved else ''}, {time.time() - start:.0f}s", flush=True)
    print(f"best validation loss {best:.3f}; checkpoint in {MODEL_DIR}", flush=True)


if __name__ == "__main__":
    main()
