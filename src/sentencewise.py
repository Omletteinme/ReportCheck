"""Sentence-by-sentence simplification with a keep-the-original fallback.

Each source sentence (unit) gets a few candidate rewrites from the generator. A rewrite is used only if it passes every
check against its own source sentence; otherwise the source sentence is kept as written, so a failed rewrite cannot
add a claim, change a hedge, move a number or drop a finding. The glossary adds term explanations at display time.

`generate_candidates` is the only step that needs the model; `assemble` is deterministic given the candidates, so a run
can be re-scored from a cache without generating again.
"""
import re
from collections import Counter

from . import numbers
from .discourse import parse_report
from .generate import sentence_prompt
from .glossary import count_terms, find_terms
from .hedge import sentence_certainty
from .verify import _fk_grade

MIN_FORWARD, MIN_BACK = 0.8, 0.6  # NLI: source entails rewrite / rewrite entails source (the latter catches dropped content)
MIN_WORDS = 4                     # shorter sentences are kept: nothing to simplify
MIN_PLAIN_SHARE = 0.5              # share of a glossary explanation's content words a rewrite must use to replace the term
MAX_GROWTH = 2.5                  # a rewrite longer than this many times the source is rejected
MIN_FK_GAIN = 0.5                 # reading-grade drop that counts as simpler

# Words a rewrite may not introduce unless the source sentence already has them: advice, reassurance, alarm.
_ADDED_RE = re.compile(
    r"\b(?:worr\w*|reassur\w*|recommend\w*|follow[- ]?up|should|need(?:s|ed)?|serious\w*|cancer\w*|urgent\w*|concern\w*|"
    r"doctor|physician|treatment|medication|surgery|emergency|dangerous|harmless|normal|healthy|fine|okay)\b", re.I)


# Content-word control. A rewrite may only (a) keep the source's medical words or replace a glossary term by its reviewed
# plain wording, and (b) add words from the source, that wording, or this closed list. Anything else is a new claim.
_STOP = frozenset("""
a an the and or but if then than so of in on at to from by with without within into onto over under above below near
around inside outside between through during this that these those it its is are was were be been being has have had do
does did not no nor there here which who whom whose what where when while as also again however otherwise may might can
could will would should shall must any some each both either other another more most less least very too only just about
approximately roughly your you we they he she their his her our out up down off per""".split())
_FREE = frozenset("noted seen present identified observed evidence demonstrated visualized findings finding evaluation".split())
_SAFE = frozenset("area areas part parts region side sides upper lower middle show shows shown sign signs found imaging image "
                  "images ray scan view views report test picture".split())
_NEGATION = re.compile(r"\b(?:no|not|without|negative|absent|never|neither|nor|none|cannot|free of)\b|n't", re.I)


def _stem(word: str) -> str:
    word = word.lower()
    word = word[:-3] + "y" if word.endswith("ies") else word[:-1] if word.endswith("s") and not word.endswith("ss") else word
    return word[:8]


def _content(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[A-Za-z]{3,}", text) if w.lower() not in _STOP and w.upper() != "XXXX"}


def _uses_plain(plain: str, out: set[str]) -> bool:
    """The rewrite used the glossary's plain wording for a term (at least MIN_PLAIN_SHARE of its content words)."""
    words = _content(plain)
    return bool(words) and len(words & out) / len(words) >= MIN_PLAIN_SHARE


def word_changes(source: str, rewrite: str) -> str | None:
    """Reason a rewrite changes the sentence's vocabulary beyond the allowed substitutions, or None."""
    src, out = _content(source), _content(rewrite)
    terms = find_terms(source)
    kept_by_gloss = set().union(*[_content(t["text"]) for t in terms if _uses_plain(t["plain"], out)], set())
    allowed_new = src | set().union(*[_content(t["plain"]) for t in terms], set()) | {_stem(w) for w in _SAFE}
    free = {_stem(w) for w in _FREE}
    dropped = src - out - kept_by_gloss - free
    if dropped:
        return "dropped word: " + ", ".join(sorted(dropped))
    new = out - allowed_new
    if new:
        return "new word: " + ", ".join(sorted(new))
    return None


def clean(text: str) -> str:
    """One line, no surrounding quotes or bullets."""
    text = " ".join(text.split()).strip("\"'`*-• ")
    return text


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text)


def rejection(source: str, rewrite: str, entail_fn=None) -> str | None:
    """Why `rewrite` may not replace `source` (None when it may). `entail_fn(premise, hypotheses)` is the NLI scorer."""
    if not rewrite:
        return "empty"
    if not rewrite.endswith((".", "!", "?")):
        return "cut off"
    if re.search(r"[()\[\]]", rewrite):
        return "parenthesis"
    if len(_words(rewrite)) > MAX_GROWTH * len(_words(source)):
        return "too long"
    added = {w.lower() for w in _ADDED_RE.findall(rewrite)} - {w.lower() for w in _ADDED_RE.findall(source)}
    if added:
        return "added " + ", ".join(sorted(added))
    cmp = numbers.compare(source, rewrite)
    if cmp["wrong_sides"]:
        return "side changed"
    if cmp["missing"] or cmp["unsupported"] or cmp["misbound"]:
        return "number changed"
    if cmp["wrong_qualifiers"] or cmp["wrong_comparisons"]:
        return "severity or comparison changed"
    if numbers.sides(source) - numbers.sides(rewrite):
        return "side dropped"  # compare() flags a missing side only when another one is named
    if cmp["score"] < 1.0:
        return "detail dropped"
    if sentence_certainty(source) != sentence_certainty(rewrite):
        return "certainty changed"
    if bool(_NEGATION.search(source)) != bool(_NEGATION.search(rewrite)):
        return "negation changed"
    changed = word_changes(source, rewrite)
    if changed:
        return changed
    simpler = _fk_grade(rewrite) <= _fk_grade(source) - MIN_FK_GAIN or count_terms(rewrite) < count_terms(source)
    if not simpler:
        return "not simpler"
    if entail_fn is not None:
        if entail_fn(source, [rewrite])[0] < MIN_FORWARD:
            return "meaning not supported"
        if entail_fn(rewrite, [source])[0] < MIN_BACK:
            return "content dropped"
    return None


def generate_candidates(generator, source: str, n: int = 3, temperature: float = 0.8,
                        max_new_tokens: int = 120) -> list[list[str]]:
    """Per source sentence: one greedy rewrite plus `n` sampled ones, deduplicated. Sentences that are kept as written
    (contain XXXX, or are very short) get no candidates."""
    units = parse_report(source).units
    result = []
    for i, unit in enumerate(units):
        if "XXXX" in unit.text or len(_words(unit.text)) < MIN_WORDS:
            result.append([])
            continue
        prompt = sentence_prompt(unit, units[i - 1].text if i else "", units[i + 1].text if i + 1 < len(units) else "")
        texts = generator.generate(prompt, n=1, max_new_tokens=max_new_tokens)
        texts += generator.generate(prompt, n=n, temperature=temperature, max_new_tokens=max_new_tokens)
        result.append(list(dict.fromkeys(t for t in map(clean, texts) if t)))
    return result


def assemble(source: str, candidates: list[list[str]], entail_fn=None) -> dict:
    """Pick the simplest rewrite that passes every check for each sentence; keep the source sentence otherwise.

    Returns {"text", "units": [{"source", "text", "status": "rewritten" | "kept", "reason", "candidates"}],
    "rewritten", "total"}.
    """
    units = parse_report(source).units
    if len(units) != len(candidates):
        raise ValueError("candidates must have one list per source sentence")
    out = []
    for unit, cands in zip(units, candidates):
        if "XXXX" in unit.text:
            reason, passing = "text removed in the report (XXXX)", []
        elif len(_words(unit.text)) < MIN_WORDS:
            reason, passing = "already short", []
        else:
            verdicts = [(c, rejection(unit.text, c, entail_fn)) for c in cands]
            passing = [c for c, why in verdicts if why is None]
            reason = Counter(why for _, why in verdicts).most_common(1)[0][0] if verdicts else "no rewrite produced"
        best = min(passing, key=_fk_grade) if passing else None
        out.append({"source": unit.text, "text": best or unit.text, "status": "rewritten" if best else "kept",
                    "reason": "" if best else reason, "candidates": cands})
    return {"text": " ".join(u["text"] for u in out), "units": out,
            "rewritten": sum(u["status"] == "rewritten" for u in out), "total": len(out)}


def simplify(generator, entail_fn, source: str, **kwargs) -> dict:
    return assemble(source, generate_candidates(generator, source, **kwargs), entail_fn)
