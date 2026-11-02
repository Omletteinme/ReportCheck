from src.bestofn import (acceptable, best_of_n, choose, looks_truncated, preference_pair, rank,
                         sample_candidates)
from src.verify import Verifier

SOURCE = (
    "FINDINGS: There is a 6 mm nodular opacity in the right lower lobe. No pleural effusion. "
    "IMPRESSION: Right lower lobe nodule, possibly infectious, though neoplasm cannot be excluded. "
    "Recommend follow-up CT in 3 months."
)
GOOD = (
    "You have a spot, 6 mm wide, in the lower part of your right lung. "
    "There is no fluid around your lungs. "
    "The spot could be an infection, but it is possible it is a tumor. "
    "Your doctor recommends another CT scan in 3 months."
)
WRONG_NUMBER = GOOD.replace("6 mm", "16 mm")
FLIPPED_HEDGE = GOOD.replace("could be an infection, but it is possible it is a tumor", "is an infection")
TRUNCATED = GOOD[:-1] + " and"


class FakeGenerator:
    """Returns the greedy text for n=1 and the sampled texts otherwise."""

    def __init__(self, greedy, sampled):
        self.greedy, self.sampled = greedy, sampled

    def generate(self, prompt, n=1, temperature=0.0, max_new_tokens=300):
        return [self.greedy] if temperature == 0 else list(self.sampled)


def verifier():
    return Verifier(entail_fn=lambda premise, hs: [0.9] * len(hs))


def test_looks_truncated():
    assert looks_truncated(TRUNCATED) and not looks_truncated(GOOD)


def test_sample_candidates_drops_empty_truncated_and_duplicates():
    gen = FakeGenerator(GOOD, [GOOD, "", TRUNCATED, WRONG_NUMBER])
    assert sample_candidates(gen, SOURCE) == [GOOD, WRONG_NUMBER]


def test_best_of_n_ranks_best_first_and_choose_returns_it():
    ranked = best_of_n(FakeGenerator(WRONG_NUMBER, [FLIPPED_HEDGE, GOOD]), verifier(), SOURCE)
    assert ranked[0].text == GOOD
    assert choose(ranked).text == GOOD
    assert [c.score.total for c in ranked] == sorted((c.score.total for c in ranked), reverse=True)


def test_acceptable_rejects_number_and_hedge_errors():
    v = verifier()
    assert acceptable(v.score(SOURCE, GOOD))
    assert not acceptable(v.score(SOURCE, WRONG_NUMBER))
    assert not acceptable(v.score(SOURCE, FLIPPED_HEDGE))


def test_choose_prefers_acceptable_over_higher_unacceptable():
    v = verifier()
    ranked = rank(v, SOURCE, [GOOD, WRONG_NUMBER])
    # force the unacceptable one to the top: choose must skip it
    ranked = [ranked[1], ranked[0]]
    assert choose(ranked).text == GOOD


def test_choose_falls_back_to_top_when_nothing_acceptable():
    ranked = rank(verifier(), SOURCE, [WRONG_NUMBER, FLIPPED_HEDGE])
    assert choose(ranked) is ranked[0]
    assert choose([]) is None


def test_preference_pair_chosen_acceptable_rejected_worst():
    ranked = rank(verifier(), SOURCE, [GOOD, FLIPPED_HEDGE, WRONG_NUMBER])
    chosen, rejected = preference_pair(ranked)
    assert chosen.text == GOOD and rejected is ranked[-1] and rejected.text != GOOD
    assert chosen.score.total - rejected.score.total >= 0.10


def test_preference_pair_none_when_gap_small_or_no_acceptable_or_single():
    v = verifier()
    assert preference_pair(rank(v, SOURCE, [GOOD])) is None  # nothing to contrast
    assert preference_pair(rank(v, SOURCE, [WRONG_NUMBER, FLIPPED_HEDGE])) is None  # no acceptable chosen
    ranked = rank(v, SOURCE, [GOOD, FLIPPED_HEDGE])
    assert preference_pair(ranked, min_gap=0.99) is None  # gap below threshold


def test_near_copy_of_source_is_never_chosen_even_if_faithful():
    v = verifier()
    copy = SOURCE.replace("FINDINGS: ", "").replace("IMPRESSION: ", "")
    score = v.score(SOURCE, copy)
    assert score.numbers == 1.0 and score.certainty >= 0.75 and score.simplicity == 0.0
    assert not acceptable(score)
    assert preference_pair(rank(v, SOURCE, [copy, FLIPPED_HEDGE])) is None


def test_extra_plain_draft_joins_the_pool_and_can_win():
    # the plain draft is GOOD; the sampler only produces worse candidates, so the verifier must keep the plain one
    ranked = best_of_n(FakeGenerator(WRONG_NUMBER, [FLIPPED_HEDGE]), verifier(), SOURCE, extra=(GOOD, GOOD, ""))
    assert choose(ranked).text == GOOD
    assert [c.text for c in ranked].count(GOOD) == 1  # duplicate extra dropped, empty extra dropped
    assert looks_truncated(TRUNCATED) and TRUNCATED not in [c.text for c in
                                                            best_of_n(FakeGenerator(GOOD, []), verifier(), SOURCE, extra=(TRUNCATED,))]
