"""Shared regex patterns for hedge, number, recommendation and normal-report detection."""
import re

# Graded hedge lexicon (Callen et al., Hanauer et al.); longest phrases first.
HEDGES = [
    "cannot be excluded", "cannot be ruled out", "can not be excluded",
    "cannot exclude", "not excluded", "may represent", "could represent",
    "suggestive of", "suspicious for", "concerning for", "compatible with",
    "consistent with", "suggests", "probable", "probably", "possible",
    "possibly", "likely", "unlikely", "questionable", "may be", "might",
    "could be", "equivocal", "indeterminate",
]
HEDGE_RE = re.compile(r"\b(" + "|".join(re.escape(h) for h in HEDGES) + r")\b", re.I)
NUMBER_RE = re.compile(
    r"\b\d+(\.\d+)?\s?(mm|cm|ml|mg|x\s?\d+|degrees?|months?|weeks?|days?|years?)\b|\b\d+(\.\d+)?\s?%",
    re.I,
)
RECOMMEND_RE = re.compile(
    r"\b(recommend|follow[- ]?up|correlat|advise|suggest(ed)? (repeat|further|clinical)|"
    r"further (evaluation|imaging|workup)|repeat (chest|imaging|radiograph))", re.I
)
NORMAL_RE = re.compile(
    r"\b(no acute (cardiopulmonary )?(abnormalit|disease|findings)|normal chest|no active disease)", re.I
)
