"""Hedge detection and calibration onto a 4-level patient certainty scale (Gap 1).

Scale (ordinal, low to high): unlikely < possible < likely < definite.
A sentence with no hedge is `definite`. With several hedges the weakest wins
("possibly consistent with X" is `possible`). The same lexicon is applied to
clinical source text and to generated patient text so certainty can be compared.
"""
import re

from .text import split_sentences

LEVELS = ["unlikely", "possible", "likely", "definite"]
RANK = {level: i for i, level in enumerate(LEVELS)}

TERMS = {
    "unlikely": ["unlikely", "not likely", "less likely", "probably not", "improbable"],
    "possible": [
        "cannot be excluded", "cannot be ruled out", "can not be excluded", "cannot exclude",
        "cannot rule out", "can not rule out", "can't rule out", "not ruled out", "unable to exclude",
        "not excluded", "can't say for sure", "may represent", "could represent", "may be",
        "could be", "might be", "possible", "possibly", "possibility", "questionable",
        "equivocal", "indeterminate", "uncertain", "not sure", "unclear", "may", "might", "could",
        "potentially",
    ],
    "likely": [
        "suggestive of", "suspicious for", "concerning for", "compatible with", "consistent with",
        "suggests", "suggest", "suggesting", "suggested", "indicative of", "favoring", "favors",
        "probable", "probably", "most likely", "likely", "likelihood", "presumably", "suspected",
        "seems", "seem", "seemed",
    ],
}
_LEVEL_OF = {term: level for level, terms in TERMS.items() for term in terms}
_HEDGE_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(_LEVEL_OF, key=len, reverse=True)) + r")\b", re.I
)

# Modals/attributions that look like hedges but are not diagnostic uncertainty.
_EXCLUDE_RE = re.compile(
    r"\b(?:could|may|might) be (?:\w+ ){0,2}(?:evaluated|performed|obtained|considered|warranted|"
    r"helpful|useful|needed|necessary|recommended|advised|indicated|confirmed|correlated|followed|"
    r"repeated|reassessed|to evaluate|to assess|to characterize)\b"
    r"|\b(?:consistent|compatible) with (?:the patient's|known|his|her|a history of|history of)\b"
    r"|\b(?:to|not|no|without) (?:\w+ ){0,2}suggest\w*\b",  # "no consolidation to suggest pneumonia"
    re.I,
)

PATIENT_PHRASE = {
    "definite": "state it plainly",
    "likely": "say it is likely / probably",
    "possible": "say it is possible / could be, and that it cannot be ruled out",
    "unlikely": "say it is unlikely",
}


def hedges(sentence: str) -> list[tuple[str, str]]:
    """(term, level) for every diagnostic hedge in the sentence."""
    cleaned = _EXCLUDE_RE.sub(" ", sentence)
    return [(m.group(0).lower(), _LEVEL_OF[m.group(0).lower()]) for m in _HEDGE_RE.finditer(cleaned)]


def sentence_certainty(sentence: str) -> str:
    found = hedges(sentence)
    return min((level for _, level in found), key=RANK.get) if found else "definite"


def certainty_profile(text: str) -> list[str]:
    """Certainty level of each hedged sentence in the text (definite sentences omitted)."""
    levels = (sentence_certainty(s) for s in split_sentences(text))
    return [level for level in levels if level != "definite"]
