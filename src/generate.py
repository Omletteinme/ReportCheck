"""Prompt construction and sampling for the simplification generator."""
import os

os.environ.setdefault("USE_TF", "0")  # global TF install clashes with protobuf

from .discourse import Report, parse_report
from .glossary import find_terms
from .hedge import PATIENT_PHRASE

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

BASELINE_PROMPT = (
    "Rewrite this radiology report in plain language for a patient. Keep every "
    "number and keep the same level of certainty. Do not add anything not in the report.\n\n"
)

# Conservative readability nudge: swap jargon, stay close to the report. Strong versions ("12-year-old")
# made the 1.5B model invent content, so this one is deliberately mild.
_PLAIN_RULE = (
    "- Use plain, clear wording a patient can follow. Replace medical jargon with simple words, and give a "
    "short plain explanation in parentheses the first time a medical term appears. Keep the report's order "
    "and keep each statement close to its original meaning.\n"
)

_RULES = (
    "Rewrite the report below in plain language for a patient, in short paragraphs, no headings or markdown.\n"
    "Rules:\n"
    "- Only cover what the units say. Write about a recommendation ONLY if a unit has role=recommendation; "
    "otherwise add no advice, follow-up or next steps.\n"
    "- Keep every number with its unit exactly; never invent a number or unit.\n"
    "- Each unit has a certainty tag. Express it: "
    + "; ".join(f"{k} = {v}" for k, v in PATIENT_PHRASE.items())
    + ". Never add hedging to a definite unit.\n"
    "- Do not add diagnoses, causes, severity words, urgency, or advice that is not in the unit.\n"
    "- Keep left/right and every size or severity word as written.\n"
    "- XXXX marks removed text: do not guess it.\n"
    "- Respect the relations: an impression summarizes its finding; a recommendation follows from its impression.\n\n"
)


def structured_prompt(report: Report, plain: bool = False) -> str:
    lines = []
    for u in report.units:
        nums = ", ".join(f"{v:g} {unit}" for v, unit in u.numbers) or "none"
        lines.append(f"[{u.id}] role={u.role} | certainty={u.certainty} | numbers={nums}\n    {u.text}")
    rels = [f"[{a}] {rel} [{b}]" for a, rel, b in report.edges] or ["none"]
    rules = _RULES.replace("Rules:\n", "Rules:\n" + _PLAIN_RULE) if plain else _RULES
    return rules + "UNITS:\n" + "\n".join(lines) + "\n\nRELATIONS: " + "; ".join(rels)


_SENTENCE_RULES = (
    "Rewrite ONE sentence of a radiology report in plain language for a patient.\n"
    "Rules:\n"
    "- Reply with the rewritten sentence only: one or two short sentences, no parentheses, lists, quotes or headings.\n"
    "- Use everyday words for medical terms when a plain word exists; otherwise keep the term as written.\n"
    "- Keep every number with its unit exactly; keep left/right and every size or severity word as written.\n"
    "- Express the certainty tag: "
    + "; ".join(f"{k} = {v}" for k, v in PATIENT_PHRASE.items())
    + ". Never add hedging to a definite sentence.\n"
    "- Add nothing: no explanations, diagnoses, causes, reassurance, advice or next steps.\n"
    "- The neighbouring sentences are context only: do not rewrite or repeat them.\n\n"
)


def sentence_prompt(unit, before: str = "", after: str = "") -> str:
    """Prompt to rewrite one report sentence (a discourse.Unit) with its neighbours as context."""
    nums = ", ".join(f"{v:g} {u}" for v, u in unit.numbers) or "none"
    terms = "; ".join(f"{t['term']} = {t['plain']}" for t in find_terms(unit.text))
    approved = f"Approved plain wording (use exactly this to replace a term, or keep the term): {terms}\n" if terms else ""
    return (_SENTENCE_RULES + f"Previous sentence: {before or 'none'}\nNext sentence: {after or 'none'}\n\n"
            f"{approved}CERTAINTY: {unit.certainty}\nNUMBERS: {nums}\nSENTENCE: {unit.text}")


def build_prompt(text: str, mode: str = "structured") -> str:
    """Modes: baseline | structured | structured_plain (structured + the mild plain-language rule)."""
    if mode == "baseline":
        return BASELINE_PROMPT + text
    if mode in ("structured", "structured_plain"):
        return structured_prompt(parse_report(text), plain=mode == "structured_plain")
    raise ValueError(f"unknown mode {mode!r}")


class Generator:
    """Loads the model lazily; samples n candidates per prompt."""

    def __init__(self, model_id: str = MODEL):
        self.model_id, self._tok, self._model = model_id, None, None

    def _load(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_id, dtype=torch.float16).cuda()

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.0, max_new_tokens: int = 300) -> list[str]:
        if self._model is None:
            self._load()
        ids = self._tok.apply_chat_template(
            [{"role": "user", "content": prompt}], add_generation_prompt=True,
            return_tensors="pt", return_dict=True,
        ).to("cuda")
        sample = temperature > 0
        out = self._model.generate(
            **ids, max_new_tokens=max_new_tokens, do_sample=sample,
            temperature=temperature if sample else None, top_p=0.95 if sample else None,
            num_return_sequences=n if sample else 1,
        )
        start = ids["input_ids"].shape[1]
        return [self._tok.decode(o[start:], skip_special_tokens=True).strip() for o in out]
