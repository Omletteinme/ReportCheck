"""The fine-tuned T5 sentence simplifier, with the same `generate` interface as generate.Generator.

Trained by scripts/train_t5.py on sentence pairs from BioLaySumm Open-i (AI-written plain-language text).
"""
import os
from pathlib import Path

os.environ.setdefault("USE_TF", "0")  # global TF install clashes with protobuf

PREFIX = "simplify: "
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "t5-lay"


def t5_prompt(unit, before: str = "", after: str = "") -> str:
    """sentencewise.generate_candidates prompt_fn: the model sees only the sentence."""
    return PREFIX + unit.text


class T5Generator:
    """Loads lazily; greedy decoding uses beam search (4 beams), temperature > 0 samples with top_p 0.95."""

    def __init__(self, path: str | Path = MODEL_DIR):
        self.path, self._tok, self._model = str(path), None, None

    def _load(self):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(self.path)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self.path).cuda().eval()

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.0, max_new_tokens: int = 128) -> list[str]:
        import torch

        if self._model is None:
            self._load()
        ids = self._tok(prompt, return_tensors="pt", truncation=True, max_length=128).to("cuda")
        sample = temperature > 0
        with torch.no_grad():
            out = self._model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=sample,
                                       temperature=temperature if sample else None, top_p=0.95 if sample else None,
                                       num_beams=1 if sample else 4, num_return_sequences=n if sample else 1)
        return [self._tok.decode(o, skip_special_tokens=True).strip() for o in out]
