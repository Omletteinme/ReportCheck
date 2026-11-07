"""Fixed plain-language glossary: attaches short explanations to medical terms in a draft.

Nothing is generated: every explanation comes from data/glossary.csv and is meant to be human-reviewed.
Each term is explained once per draft, after its first occurrence, as "term (explanation)". The verifier
drops parenthetical text before its meaning check, and the glossary content guard in tests keeps explanations
free of hedges, sides, severity words and numbers, so glossed drafts score the same as unglossed ones.
"""
import csv
import re
from functools import lru_cache
from pathlib import Path

from .text import split_sentences

PATH = Path(__file__).resolve().parent.parent / "data" / "glossary.csv"


@lru_cache(maxsize=1)
def load() -> list[dict]:
    with PATH.open(encoding="utf-8", newline="") as f:
        return [{"term": r["term"].strip(), "plain": r["plain"].strip(),
                 "variants": [v.strip() for v in r["variants"].split(";") if v.strip()]}
                for r in csv.DictReader(f)]


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, dict], re.Pattern]:
    forms = {form.lower(): entry for entry in load() for form in [entry["term"], *entry["variants"]]}
    longest_first = sorted(forms, key=len, reverse=True)
    pattern = re.compile(r"(?<![A-Za-z])(?:" + "|".join(re.escape(f) for f in longest_first) + r")(?![A-Za-z])", re.I)
    return forms, pattern


def find_terms(text: str) -> list[dict]:
    """[{term, text, plain}] for each glossary term in the text, once per term, in order of appearance."""
    forms, pattern = _index()
    found: dict[str, dict] = {}
    for m in pattern.finditer(text):
        entry = forms[m.group(0).lower()]
        found.setdefault(entry["term"], {"term": entry["term"], "text": m.group(0), "plain": entry["plain"]})
    return list(found.values())


def count_terms(text: str) -> int:
    """How many glossary terms the text contains (a proxy for how technical it still is)."""
    return len(_index()[1].findall(text))


def gloss_sentences(sentences: list[str], max_glosses: int | None = None) -> list[dict]:
    """[{text, glossed, parts, terms}] per sentence; each term is explained only at its first occurrence overall.

    `parts` is [(text, is_explanation)] so a page can style explanations; `glossed` is the same text joined.
    A term is skipped when it is already followed by "(" or sits inside parentheses.
    """
    forms, pattern = _index()
    seen: set[str] = set()
    result = []
    for text in sentences:
        terms, parts, pos = [], [], 0
        for m in pattern.finditer(text):
            entry = forms[m.group(0).lower()]
            before = text[:m.start()]
            if (entry["term"] in seen or before.count("(") > before.count(")")
                    or text[m.end():].lstrip().startswith("(")
                    or (max_glosses is not None and len(seen) >= max_glosses)):
                continue
            seen.add(entry["term"])
            terms.append(entry["term"])
            parts += [(text[pos:m.end()], False), (f" ({entry['plain']})", True)]
            pos = m.end()
        parts.append((text[pos:], False))
        result.append({"text": text, "glossed": "".join(t for t, _ in parts), "parts": parts, "terms": terms})
    return result


def gloss(text: str, max_glosses: int | None = None) -> str:
    """The whole draft as one string with explanations inserted."""
    return " ".join(s["glossed"] for s in gloss_sentences(split_sentences(text), max_glosses))


def annotate(sentences: list[dict]) -> list[dict]:
    """Add `parts` and `gloss_terms` to Verifier.explain()["sentences"]; scores and flags stay on the model's text."""
    glossed = gloss_sentences([s["text"] for s in sentences])
    return [{**s, "parts": [{"t": t, "gloss": g} for t, g in x["parts"]], "gloss_terms": x["terms"]}
            for s, x in zip(sentences, glossed)]
