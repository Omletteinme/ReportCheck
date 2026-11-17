"""Sentence-level training pairs from report / plain-language-report pairs (BioLaySumm Open-i).

A pair is only used when both texts have the same number of sentences, so sentence i of the report matches sentence i of
the plain-language version (a different count means the writer split or merged sentences and pairing would be a guess).
Each sentence pair must also pass the same meaning checks the system applies to its own output.
"""
import random
import re

from .sentencewise import MIN_WORDS, rejection
from .text import split_sentences

_LABELS = re.compile(r"\b(?:findings|impression|comparison|indication)\s*:", re.I)


def normalize(text: str) -> str:
    """Lowercase text without section labels or punctuation, to match the same report across formats."""
    return re.sub(r"\W+", " ", _LABELS.sub(" ", text.lower())).strip()


def align(source: str, lay: str) -> list[tuple[str, str]]:
    """Sentence pairs in order, or [] when the two texts do not have the same number of sentences."""
    src, out = split_sentences(source), split_sentences(lay)
    return list(zip(src, out)) if len(src) == len(out) else []


def sentence_pairs(source: str, lay: str) -> list[tuple[str, str]]:
    """Aligned sentence pairs that are worth learning from: the source sentence is rewritable (no XXXX, long enough) and the
    plain-language sentence passes every meaning check (numbers, sides, severity, hedge, negation, added advice, simpler)."""
    return [(s, l) for s, l in align(source, lay)
            if "XXXX" not in s and len(s.split()) >= MIN_WORDS and rejection(s, l, None, vocab=False) is None]


def split_by_id(pairs: list[dict], val_fraction: float = 0.1, seed: int = 0) -> tuple[list[dict], list[dict]]:
    """(train, validation) with every report id on one side only; pairs are dicts with an "rid" key."""
    ids = sorted({p["rid"] for p in pairs})
    random.Random(seed).shuffle(ids)
    val_ids = set(ids[:max(1, round(len(ids) * val_fraction))])
    return [p for p in pairs if p["rid"] not in val_ids], [p for p in pairs if p["rid"] in val_ids]
