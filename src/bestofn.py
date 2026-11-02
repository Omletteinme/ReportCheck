"""Best-of-N selection and preference-pair construction with the verifier as the reward.

Candidates are sampled from the structured prompt (plus one greedy anchor). A response may only be
*chosen* if it passes the hard checks below; the *rejected* side is the lowest-scoring candidate.
"""
from dataclasses import dataclass

from .generate import build_prompt
from .verify import Score, Verifier

MIN_GAP = 0.10  # chosen must beat rejected by this much total score
MIN_NUMBERS, MIN_CERTAINTY, MIN_ENTAIL = 1.0, 0.75, 0.7  # hard checks for a chosen response
# Near-copies of the source are faithful but unsimplified; 0.1 = at least half a reading grade easier.
MIN_SIMPLICITY = 0.1


@dataclass
class Candidate:
    text: str
    score: Score


def looks_truncated(text: str) -> bool:
    """Heuristic for generation cut off at max_new_tokens: no sentence-final character at the end."""
    return not text.rstrip().endswith((".", "!", "?", ")", '"', "*"))


def sample_candidates(generator, source: str, n: int = 8, temperature: float = 0.8,
                      max_new_tokens: int = 320) -> list[str]:
    """Per prompt mode (structured, structured_plain): one greedy anchor plus n // 2 samples.

    Mixing the mild plain-language prompt in gives the pool some genuinely simpler candidates; training
    pairs still use the plain structured prompt. Empty, truncated and duplicate texts are dropped.
    """
    texts: list[str] = []
    for mode in ("structured", "structured_plain"):
        prompt = build_prompt(source, mode)
        texts += generator.generate(prompt, n=1, max_new_tokens=max_new_tokens)
        texts += generator.generate(prompt, n=max(n // 2, 1), temperature=temperature, max_new_tokens=max_new_tokens)
    kept: list[str] = []
    for text in texts:
        if text and not looks_truncated(text) and text not in kept:
            kept.append(text)
    return kept


def rank(verifier: Verifier, source: str, texts: list[str]) -> list[Candidate]:
    """Candidates sorted best first."""
    return [Candidate(text, score) for score, text in verifier.rank(source, texts)]


def acceptable(score: Score) -> bool:
    return (score.numbers >= MIN_NUMBERS and score.certainty >= MIN_CERTAINTY
            and score.entail >= MIN_ENTAIL and score.simplicity >= MIN_SIMPLICITY)


def choose(ranked: list[Candidate]) -> Candidate | None:
    """Best-of-N: the top acceptable candidate; falls back to the top scorer when none is acceptable."""
    return next((c for c in ranked if acceptable(c.score)), ranked[0] if ranked else None)


def preference_pair(ranked: list[Candidate], min_gap: float = MIN_GAP) -> tuple[Candidate, Candidate] | None:
    """(chosen, rejected) or None when no acceptable chosen exists or the gap is too small to trust."""
    chosen = next((c for c in ranked if acceptable(c.score)), None)
    if chosen is None or chosen is ranked[-1]:
        return None
    rejected = ranked[-1]
    return (chosen, rejected) if chosen.score.total - rejected.score.total >= min_gap else None


def best_of_n(generator, verifier: Verifier, source: str, n: int = 8, extra: tuple[str, ...] = (),
              **kwargs) -> list[Candidate]:
    """Ranked candidates for the source; use `choose` to pick the output.

    `extra` texts (for example the plain draft the user would otherwise get) join the pool, so the verifier
    can keep them; empty, truncated and duplicate extras are dropped like any other candidate.
    """
    texts = sample_candidates(generator, source, n, **kwargs)
    texts += [t for t in dict.fromkeys(extra) if t and not looks_truncated(t) and t not in texts]
    return rank(verifier, source, texts)
