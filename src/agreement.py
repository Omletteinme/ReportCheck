"""Small statistics helpers for label agreement and verifier evaluation (binary labels)."""


def auc(scores: list[float], bad: list[bool]) -> float:
    """P(a random clean item outscores a random errored item); ties count half. NaN if one class is empty."""
    good_s = [s for s, b in zip(scores, bad) if not b]
    bad_s = [s for s, b in zip(scores, bad) if b]
    if not good_s or not bad_s:
        return float("nan")
    return sum((g > b) + 0.5 * (g == b) for g in good_s for b in bad_s) / (len(good_s) * len(bad_s))


def cohen_kappa(a: list[int], b: list[int]) -> float:
    """Chance-corrected agreement of two binary labelers; NaN when chance agreement is already 1."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return float("nan") if expected == 1 else (observed - expected) / (1 - expected)


def majority(labelers: list[list[int]]) -> list[int]:
    """Per item, 1 when at least half of the labelers say 1 (ties flag the item, the conservative choice)."""
    n = len(labelers)
    return [int(2 * sum(item) >= n) for item in zip(*labelers)]
