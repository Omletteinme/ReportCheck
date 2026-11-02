"""Sentence splitting shared by hedge, numbers, discourse and verify."""
import re

# a line that is only a short bold title, e.g. "**Radiology Report Summary**" (no sentence punctuation)
_BOLD_HEADING_RE = re.compile(r"\s*(?:[-*]\s+)?\*\*[^*.!?]{1,60}\*\*\s*")
_SECTION_RE = re.compile(r"\b(?:FINDINGS|IMPRESSION):", re.I)
# split after a sentence end preceded by a letter/paren/%; never after "1." list markers
_SPLIT_RE = re.compile(r"(?<=[A-Za-z\)\]%\"'][.!?])\s+(?=[A-Z0-9*\"(])")


def strip_markdown(line: str) -> str:
    line = re.sub(r"\*\*|__|`", "", line)
    return re.sub(r"^\s*(?:[-*#>]+|\d+\))\s*", "", line).strip()


def split_sentences(text: str) -> list[str]:
    """Split plain or markdown text into sentences; drops section labels, markdown headings and bare titles."""
    sentences = []
    for raw in text.splitlines():
        if raw.lstrip().startswith("#") or _BOLD_HEADING_RE.fullmatch(raw):
            continue
        for line in _SECTION_RE.sub("\n", strip_markdown(raw)).splitlines():
            for s in _SPLIT_RE.split(line.strip()):
                s = re.sub(r"^\d+\.\s+", "", s.strip())  # drop "1. " list markers
                if not s or (s.endswith(":") and len(s.split()) <= 4):
                    continue
                sentences.append(s)
    return sentences
