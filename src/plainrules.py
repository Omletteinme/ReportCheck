"""Rule-based plain-language rewriting from a reviewed table (data/plain_rules.csv).

Nothing is generated: each rule swaps a medical word or stock phrase for plain wording, in file order (specific rules
first). After the swaps every sentence is compared with its source on numbers, sides, severity group, hedge level
and negation; a sentence that fails any of these is kept as written, so a bad rule cannot change what the report says.
"""
import csv
import re
from functools import lru_cache
from pathlib import Path

from . import numbers
from .hedge import sentence_certainty
from .text import split_sentences

PATH = Path(__file__).resolve().parent.parent / "data" / "plain_rules.csv"
NEGATION = re.compile(r"\b(?:no|not|without|negative|absent|never|neither|nor|none|cannot|free of)\b|n't", re.I)


@lru_cache(maxsize=1)
def load() -> list[tuple[re.Pattern, str, str]]:
    """[(compiled pattern, replacement, source pattern)] in file order."""
    with PATH.open(encoding="utf-8", newline="") as f:
        return [(re.compile(rf"(?<![A-Za-z])(?:{r['pattern']})(?![A-Za-z])", re.I), r["replacement"], r["pattern"])
                for r in csv.DictReader(f)]


def _swap(pattern: re.Pattern, replacement: str, text: str) -> str:
    def sub(m):
        out = m.expand(replacement)
        return out[0].upper() + out[1:] if m.group(0)[0].isupper() else out
    return pattern.sub(sub, text)


def meaning_changes(source: str, rewrite: str) -> list[str]:
    """What a rewrite changed about numbers, sides, severity, certainty or negation (empty when nothing)."""
    cmp = numbers.compare(source, rewrite)
    problems = []
    if cmp["missing"] or cmp["unsupported"] or cmp["misbound"]:
        problems.append("number")
    if numbers.sides(source) != numbers.sides(rewrite):
        problems.append("side")
    if numbers.qualifier_groups(source) != numbers.qualifier_groups(rewrite) or cmp["wrong_comparisons"]:
        problems.append("severity or comparison")
    if sentence_certainty(source) != sentence_certainty(rewrite):
        problems.append("certainty")
    if bool(NEGATION.search(source)) != bool(NEGATION.search(rewrite)):
        problems.append("negation")
    return problems


def simplify_sentence(sentence: str) -> tuple[str, list[str], list[str]]:
    """(text, rules applied, problems). Falls back to the sentence itself when a swap changed its meaning."""
    text, applied = sentence, []
    for pattern, replacement, source_pattern in load():
        swapped = _swap(pattern, replacement, text)
        if swapped != text:
            text, applied = swapped, applied + [source_pattern]
    text = re.sub(r"\s+", " ", text).strip()
    problems = meaning_changes(sentence, text)
    return (sentence, [], problems) if problems else (text, applied, [])


def simplify(source: str) -> dict:
    """{"text", "sentences": [{"source", "text", "rules", "kept"}], "changed", "total"} for a whole report."""
    out = []
    for sentence in split_sentences(source):
        text, rules, problems = simplify_sentence(sentence)
        out.append({"source": sentence, "text": text, "rules": rules, "kept": bool(problems) and sentence == text,
                    "problems": problems})
    return {"text": " ".join(s["text"] for s in out), "sentences": out,
            "changed": sum(s["text"] != s["source"] for s in out), "total": len(out)}
