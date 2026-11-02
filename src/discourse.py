"""Rule-based discourse parsing (Gap 2): role-tagged units plus relations between them.

Roles: finding | impression | recommendation.
Relations: `summarizes` (impression -> finding with most shared content words) and
`motivated_by` (recommendation -> nearest preceding impression, else best-overlap finding).
"""
import re
from dataclasses import dataclass, field

from . import numbers
from .hedge import _EXCLUDE_RE, sentence_certainty
from .patterns import RECOMMEND_RE
from .text import split_sentences

_SECTION_SPLIT = re.compile(r"\b(FINDINGS|IMPRESSION):", re.I)
_STOP = {"with", "that", "this", "there", "have", "from", "which", "were", "been", "does", "than",
         "also", "within", "without", "again", "noted", "seen", "identified", "evidence"}


@dataclass
class Unit:
    id: int
    role: str
    text: str
    certainty: str
    numbers: list = field(default_factory=list)


@dataclass
class Report:
    units: list[Unit]
    edges: list[tuple[int, str, int]]  # (from_id, relation, to_id)


def _words(text: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _STOP}


def _sections(text: str) -> list[tuple[str, str]]:
    """(section, body) pairs in order; a label may repeat (some reports restate FINDINGS), so no dict."""
    parts = _SECTION_SPLIT.split(text)
    if len(parts) == 1:
        return [("findings", text)]
    return [(parts[i].lower(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def _role(sentence: str, section: str) -> str:
    if RECOMMEND_RE.search(sentence) or _EXCLUDE_RE.search(sentence):
        return "recommendation"
    return "impression" if section == "impression" else "finding"


def parse_report(text: str) -> Report:
    units: list[Unit] = []
    for section, body in _sections(text):
        for sentence in split_sentences(body):
            units.append(Unit(
                id=len(units) + 1,
                role=_role(sentence, section),
                text=sentence,
                certainty=sentence_certainty(sentence),
                numbers=numbers.extract(sentence),
            ))

    def best_finding(unit: Unit) -> Unit | None:
        findings = [u for u in units if u.role == "finding"]
        scored = [(len(_words(unit.text) & _words(f.text)), -f.id, f) for f in findings]
        scored = [s for s in scored if s[0] > 0]
        return max(scored)[2] if scored else None

    edges = []
    for unit in units:
        if unit.role == "impression" and (target := best_finding(unit)):
            edges.append((unit.id, "summarizes", target.id))
        elif unit.role == "recommendation":
            prior = [u for u in units if u.role == "impression" and u.id < unit.id]
            target = prior[-1] if prior else best_finding(unit)
            if target:
                edges.append((unit.id, "motivated_by", target.id))
    return Report(units, edges)
