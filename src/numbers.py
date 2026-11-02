"""Fact extraction and source-vs-output comparison: numbers, laterality, severity qualifiers.

Limitation: facts are matched as sets/multisets, not bound to the finding they belong to, so a
correct number or side attached to the wrong finding is not caught here.
"""
import re

_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split())}
_UNITS = {
    "mm": "mm", "millimeter": "mm", "millimeters": "mm", "millimetre": "mm", "millimetres": "mm",
    "cm": "cm", "centimeter": "cm", "centimeters": "cm", "centimetre": "cm", "centimetres": "cm",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml", "mg": "mg",
    "%": "%", "percent": "%", "hu": "hu", "hounsfield": "hu",
    "month": "month", "months": "month", "week": "week", "weeks": "week",
    "day": "day", "days": "day", "year": "year", "years": "year",
    "hour": "hour", "hours": "hour", "degree": "degree", "degrees": "degree",
}
_UNIT_PAT = "|".join(sorted((re.escape(u) for u in _UNITS), key=len, reverse=True))
_WORD_PAT = "|".join(_WORDS)
_WITH_UNIT = re.compile(
    rf"(?<![\w.])(?P<val>\d+(?:\.\d+)?|{_WORD_PAT})\s?(?P<unit>{_UNIT_PAT})(?![A-Za-z])", re.I
)
_BARE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w%]|\.\d|\.\s|\.$)")

Fact = tuple[float, str | None]

_SIDE_WORDS = {"left": {"left"}, "right": {"right"}, "bilateral": {"left", "right"},
               "bilaterally": {"left", "right"}, "both": {"left", "right"}}
_QUALIFIERS = {
    "low": {"mild", "mildly", "minimal", "slight", "slightly", "small", "tiny", "minor"},
    "mid": {"moderate", "moderately"},
    "high": {"severe", "severely", "marked", "markedly", "large", "massive", "extensive", "significant",
             "significantly"},
}
_NEGATED_QUALIFIER = re.compile(
    r"(?<![a-z])(?:no|not|without|nor)\s+(?:\w+\s+)?(?:" + "|".join(w for g in _QUALIFIERS.values() for w in g) + r")(?![a-z])", re.I
)


def _canon(value: str, unit: str) -> Fact:
    v = float(_WORDS.get(value.lower(), value) if not value[0].isdigit() else value)
    u = _UNITS[unit.lower()]
    return (v * 10, "mm") if u == "cm" else (v, u)


def find_facts(text: str) -> list[tuple[Fact, str]]:
    """Unit facts (cm normalised to mm) with the exact matched text, for highlighting."""
    return [(_canon(m["val"], m["unit"]), m.group(0)) for m in _WITH_UNIT.finditer(text)]


def extract(text: str) -> list[Fact]:
    """Facts that carry a unit (cm is normalised to mm)."""
    return [fact for fact, _ in find_facts(text)]


def extract_source(text: str) -> list[Fact]:
    """Unit facts plus bare numbers (unit None), which may match any unit in the output."""
    covered = [m.span() for m in _WITH_UNIT.finditer(text)]
    bare = [
        (float(m.group()), None)
        for m in _BARE.finditer(text)
        if not any(a <= m.start() < b for a, b in covered)
    ]
    return extract(text) + bare


def _matches(a: Fact, b: Fact) -> bool:
    return abs(a[0] - b[0]) < 1e-6 and (a[1] is None or b[1] is None or a[1] == b[1])


def _unmatched(items: list[Fact], pool: list[Fact]) -> list[Fact]:
    pool = list(pool)
    missing = []
    for item in items:
        hit = next((p for p in pool if _matches(item, p)), None)
        if hit is None:
            missing.append(item)
        else:
            pool.remove(hit)
    return missing


# "right"/"left" that are not a side: "right now", "all right", "nothing left", "left over"
_NOT_A_SIDE = re.compile(
    r"\b(?:right (?:now|away|here|there|place|time|amount|size|thing|way)|all right|that's right|"
    r"left (?:over|behind)|(?:nothing|is|are|has|have|was|were|any|none) left)\b", re.I
)


def side_words(text: str) -> list[tuple[str, set[str]]]:
    """(word, sides) for every left/right/bilateral/both word in the text (idioms like "right now" excluded)."""
    cleaned = _NOT_A_SIDE.sub(" ", text.lower())
    return [(w, _SIDE_WORDS[w]) for w in re.findall(r"[a-z]+", cleaned) if w in _SIDE_WORDS]


def sides(text: str) -> set[str]:
    return set().union(*(s for _, s in side_words(text)))


def qualifier_words(text: str) -> list[tuple[str, str]]:
    """(word, group) for each severity word (low/mid/high) asserted in the text; negated uses are ignored."""
    words = re.findall(r"[a-z]+", _NEGATED_QUALIFIER.sub(" ", text.lower()))
    return [(w, g) for w in words for g, terms in _QUALIFIERS.items() if w in terms]


def qualifier_groups(text: str) -> set[str]:
    """Severity groups (low/mid/high) asserted in the text; negated uses ("no significant") are ignored."""
    return {group for _, group in qualifier_words(text)}


def compare(source: str, output: str) -> dict:
    """missing/unsupported numbers, plus unsupported sides and severity groups; score in [0, 1].

    score = number F1 - 0.25 per unsupported side - 0.125 per missing side - 0.25 per unsupported severity group.
    """
    src, out = extract_source(source), extract(output)
    src_units = [f for f in src if f[1] is not None]
    missing = _unmatched(src_units, out)
    unsupported = _unmatched(out, src)
    recall = 1 - len(missing) / len(src_units) if src_units else 1.0
    precision = 1 - len(unsupported) / len(out) if out else 1.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    src_sides, out_sides = sides(source), sides(output)
    wrong_sides, missing_sides = out_sides - src_sides, (src_sides - out_sides) if out_sides else set()
    wrong_quals = qualifier_groups(output) - qualifier_groups(source)
    score = max(0.0, score - 0.25 * len(wrong_sides) - 0.125 * len(missing_sides) - 0.25 * len(wrong_quals))
    return {"missing": missing, "unsupported": unsupported, "wrong_sides": wrong_sides,
            "wrong_qualifiers": wrong_quals, "score": score}
