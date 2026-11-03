"""Verifier stack (Gap 3): entailment + numeric fidelity + certainty match + simplicity.

Used as the best-of-N selector now and as the preference/reward signal for DPO later.
Higher is better; every component and the total are in [0, 1]. `coverage` is the omission check: the
clinically loaded source sentences (impression, recommendations, hedged/measured/graded findings) must be
entailed by the output.
"""
import os
import re
from dataclasses import dataclass, field

os.environ.setdefault("USE_TF", "0")  # global TF install clashes with protobuf

from . import numbers
from .discourse import parse_report
from .hedge import RANK, certainty_profile, hedges, sentence_certainty
from .text import split_sentences

NLI_MODEL = "cross-encoder/nli-deberta-v3-base"
WEIGHTS = {"entail": 0.2975, "numbers": 0.2125, "certainty": 0.2125, "simplicity": 0.1275, "coverage": 0.15}
SUPPORT_FLAG = 0.5  # an output sentence supported less than this is flagged "unsupported" in explain()
COVERAGE_FLAG = 0.3  # a key source sentence the output supports less than this is listed as possibly omitted


class NliEntailer:
    """P(premise entails hypothesis) from a cross-encoder NLI model; loaded lazily."""

    def __init__(self, model_id: str = NLI_MODEL, device: str | None = None):
        self.model_id, self.device, self._tok, self._model = model_id, device, None, None

    def _load(self):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._tok = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_id).to(self.device).eval()
        labels = {i: l.lower() for i, l in self._model.config.id2label.items()}
        self._entail = next(i for i, l in labels.items() if l == "entailment")

    def __call__(self, premise: str, hypotheses: list[str]) -> list[float]:
        import torch

        if self._model is None:
            self._load()
        batch = self._tok([premise] * len(hypotheses), hypotheses, truncation=True, max_length=512,
                          padding=True, return_tensors="pt").to(self.device)
        with torch.no_grad():
            probs = self._model(**batch).logits.softmax(-1)
        return probs[:, self._entail].tolist()


def certainty_score(source: str, output: str) -> float:
    """1 = every distinct source hedge level reappears in the output and none are added.

    Levels are compared as sets: a hedge repeated in findings and impression may be stated once.
    """
    src_all, out_all = certainty_profile(source), certainty_profile(output)
    src = sorted({RANK[l] for l in src_all})
    out = sorted({RANK[l] for l in out_all})
    if not src and not out:
        return 1.0
    denom = max(len(src), len(out))
    cost = 0.0
    for s in src:
        if out:
            j = min(range(len(out)), key=lambda k: abs(out[k] - s))
            cost += abs(out.pop(j) - s) / 2  # unlikely/possible/likely span 2 steps
        else:
            cost += 1.0  # hedge dropped (stated as fact)
    cost += 0.5 * len(out)  # hedge levels added that the source never had
    cost += 0.5 * max(0, len(out_all) - max(len(src_all), 1))  # more hedged sentences than the source has
    return max(0.0, 1 - cost / denom)


def _fk_grade(text: str) -> float:
    import textstat

    return textstat.flesch_kincaid_grade(text)


def simplicity_score(source: str, output: str) -> float:
    """Readability gain vs source; zero for near-copies and for outputs that drop most content."""
    src_words, out_words = set(re.findall(r"\w+", source.lower())), set(re.findall(r"\w+", output.lower()))
    n_src, n_out = len(source.split()), len(output.split())
    if not out_words or n_out < 0.4 * n_src:
        return 0.0
    if len(src_words & out_words) / len(src_words | out_words) > 0.85:  # copying the source
        return 0.0
    gain = (_fk_grade(source) - _fk_grade(output)) / 5
    return min(1.0, max(0.0, gain)) * (0.5 if n_out > 3 * n_src else 1.0)


# Plain negatives and normal findings: leaving them out is not an omission ("No pneumothorax.", "Heart size is normal.")
_NORMAL_RE = re.compile(
    r"^(?:there (?:is|are) )?no\b|\bno (?:acute|focal|evidence|definite|pleural|pneumothorax|significant)\b"
    r"|\bwithin normal limits\b|\bunremarkable\b|\bnormal (?:in|size|appearance|contour|heart|cardiac|mediastinal)\b"
    r"|\b(?:lungs?|chest) (?:(?:is|are) )?clear\b|\bintact\b", re.I)


def key_sentences(source: str) -> list[str]:
    """Source sentences whose loss would change what the patient is told: impression and recommendation sentences
    that are not plain normals, plus findings that carry a hedge, a measurement or a severity word."""
    keep = []
    for unit in parse_report(source).units:
        loaded = unit.certainty != "definite" or unit.numbers or numbers.qualifier_groups(unit.text)
        normal = _NORMAL_RE.search(unit.text)
        if unit.role == "recommendation" or (unit.role == "impression" and not normal) \
                or (unit.role == "finding" and loaded and not normal):
            keep.append(unit.text)
    return keep


@dataclass
class Score:
    entail: float
    numbers: float
    certainty: float
    simplicity: float
    total: float
    details: dict = field(default_factory=dict)
    coverage: float = 1.0


class Verifier:
    def __init__(self, entail_fn=None, weights: dict | None = None):
        self.entail_fn = entail_fn or NliEntailer()
        self.weights = weights or WEIGHTS

    def support(self, source: str, output: str) -> list[tuple[str, float]]:
        """SummaC-style: each output sentence takes its best support over the whole source and each
        source sentence. Parenthetical glosses ("(pleural effusion)") are dropped from the scored
        hypothesis because they only name terms; the returned sentence keeps them."""
        pairs = [(s, re.sub(r"\s*\([^)]*\)", "", s).strip()) for s in split_sentences(output)]
        pairs = [(s, h) for s, h in pairs if h]
        if not pairs:
            return []
        hypotheses = [h for _, h in pairs]
        sentences = split_sentences(source)
        best = [0.0] * len(hypotheses)
        for premise in [" ".join(sentences)] + sentences:
            best = [max(b, p) for b, p in zip(best, self.entail_fn(premise, hypotheses))]
        return [(s, p) for (s, _), p in zip(pairs, best)]

    def coverage(self, source: str, output: str) -> list[tuple[str, float]]:
        """Reverse check: each key source sentence with its best support from the whole output, one output sentence or
        two adjacent ones (a finding is often split across lines). Glosses stay in: they are the model's own words and
        often carry the term. Empty when the source has no key sentences."""
        keys = key_sentences(source)
        if not keys:
            return []
        sentences = split_sentences(output)
        if not sentences:
            return [(k, 0.0) for k in keys]
        best = [0.0] * len(keys)
        pairs = [" ".join(sentences[i:i + 2]) for i in range(len(sentences) - 1)]
        for premise in [" ".join(sentences)] + sentences + pairs:
            best = [max(b, p) for b, p in zip(best, self.entail_fn(premise, keys))]
        return list(zip(keys, best))

    def entailment(self, source: str, output: str) -> float:
        """Mean support over the output sentences."""
        probs = [p for _, p in self.support(source, output)]
        return sum(probs) / len(probs) if probs else 0.0

    def _score(self, source: str, output: str, support: list[tuple[str, float]],
               covered: list[tuple[str, float]] | None = None) -> Score:
        num = numbers.compare(source, output)
        covered = self.coverage(source, output) if covered is None else covered
        parts = {
            "entail": sum(p for _, p in support) / len(support) if support else 0.0,
            "numbers": num["score"],
            "certainty": certainty_score(source, output),
            "simplicity": simplicity_score(source, output),
            "coverage": sum(p for _, p in covered) / len(covered) if covered else 1.0,
        }
        total = sum(self.weights[k] * v for k, v in parts.items())
        return Score(**parts, total=total, details={"missing": num["missing"], "unsupported": num["unsupported"]})

    def score(self, source: str, output: str) -> Score:
        return self._score(source, output, self.support(source, output))

    def explain(self, source: str, output: str) -> dict:
        """Score plus what to highlight: per output sentence its support, hedge level and flagged terms."""
        support, covered = self.support(source, output), self.coverage(source, output)
        score = self._score(source, output, support, covered)
        num = numbers.compare(source, output)
        bad_facts, misbound = set(num["unsupported"]), set(num["misbound"])
        src_levels = {sentence_certainty(s) for s in split_sentences(source)} - {"definite"}
        sentences = []
        for text, prob in support:
            found = hedges(text)
            level = sentence_certainty(text)
            flags: list[dict] = []
            if prob < SUPPORT_FLAG:
                flags.append({"kind": "unsupported", "terms": []})
            wrong = [m for fact, m in numbers.find_facts(text) if fact in bad_facts]
            if wrong:
                flags.append({"kind": "wrong number", "terms": wrong})
            misplaced = [m for fact, m in numbers.find_facts(text) if fact in misbound]
            if misplaced:
                flags.append({"kind": "number on wrong side", "terms": misplaced})
            side = [w for w, s in numbers.side_words(text) if s & num["wrong_sides"]]
            if side:
                flags.append({"kind": "wrong side", "terms": side})
            added = [w for w, g in numbers.qualifier_words(text) if g in num["wrong_qualifiers"]]
            if added:
                flags.append({"kind": "added severity", "terms": added})
            compared = [c["word"] for c in numbers.comparisons(text) if c["word"] in num["wrong_comparisons"]]
            if compared:
                flags.append({"kind": "added comparison", "terms": compared})
            if found and level not in src_levels:
                flags.append({"kind": "hedge changed", "terms": [t for t, _ in found]})
            sentences.append({"text": text, "support": prob, "level": level,
                              "hedge_terms": [t for t, _ in found], "flags": flags})
        source_sentences = [{"text": s, "level": sentence_certainty(s), "hedge_terms": [t for t, _ in hedges(s)]}
                            for s in split_sentences(source)]
        out_levels = {s["level"] for s in sentences} - {"definite"}
        fmt = lambda facts: [f"{v:g} {u}" if u else f"{v:g}" for v, u in facts]  # noqa: E731
        return {
            "score": {"entail": score.entail, "numbers": score.numbers, "certainty": score.certainty,
                      "simplicity": score.simplicity, "coverage": score.coverage, "total": score.total},
            "sentences": sentences,
            "source_sentences": source_sentences,
            "summary": {"missing_numbers": fmt(num["missing"]), "unsupported_numbers": fmt(num["unsupported"]),
                        "wrong_sides": sorted(num["wrong_sides"]), "wrong_qualifiers": sorted(num["wrong_qualifiers"]),
                        "wrong_comparisons": sorted(set(num["wrong_comparisons"])),
                        "misplaced_numbers": fmt(num["misbound"]),
                        "possibly_omitted": [k for k, p in covered if p < COVERAGE_FLAG],
                        "source_levels": sorted(src_levels, key=RANK.get),
                        "output_levels": sorted(out_levels, key=RANK.get),
                        "dropped_levels": sorted(src_levels - out_levels, key=RANK.get)},
        }

    def rank(self, source: str, candidates: list[str]) -> list[tuple[Score, str]]:
        """Best-of-N: candidates sorted best first."""
        return sorted(((self.score(source, c), c) for c in candidates), key=lambda x: x[0].total, reverse=True)
