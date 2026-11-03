import os

import pytest

from src.verify import Verifier, certainty_score, simplicity_score

SOURCE = (
    "FINDINGS: There is a 6 mm nodular opacity in the right lower lobe. No pleural effusion. "
    "IMPRESSION: Right lower lobe nodule, possibly infectious, though neoplasm cannot be excluded. "
    "Recommend follow-up CT in 3 months."
)
GOOD = (
    "You have a small spot, 6 mm wide, in the lower part of your right lung. "
    "There is no fluid around your lungs. "
    "The spot could be an infection, but it is possible it is a tumor. "
    "Your doctor recommends another CT scan in 3 months."
)
DROPPED_NUMBER = GOOD.replace("6 mm wide", "wide").replace("3 months", "a few months")
FLIPPED_HEDGE = (
    "You have a small spot, 6 mm wide, in the lower part of your right lung. "
    "There is no fluid around your lungs. "
    "The spot is an infection. "
    "Your doctor recommends another CT scan in 3 months."
)
WRONG_NUMBER = GOOD.replace("6 mm", "16 mm")


def always_entailed(premise, hypotheses):
    return [0.9] * len(hypotheses)


@pytest.fixture
def verifier():
    return Verifier(entail_fn=always_entailed)


def test_certainty_score():
    assert certainty_score(SOURCE, GOOD) > 0.7
    assert certainty_score(SOURCE, FLIPPED_HEDGE) == 0.0  # all hedges dropped
    assert certainty_score("The lungs are clear.", "The lungs are clear.") == 1.0
    assert certainty_score("The lungs are clear.", "The lungs might be clear.") == 0.5  # hedge added


def test_simplicity_blocks_copying_and_truncation():
    assert simplicity_score(SOURCE, SOURCE) == 0.0
    assert simplicity_score(SOURCE, "Spot.") == 0.0
    assert simplicity_score(SOURCE, GOOD) > 0


def test_good_output_beats_each_failure_mode(verifier):
    good = verifier.score(SOURCE, GOOD)
    for bad in (DROPPED_NUMBER, FLIPPED_HEDGE, WRONG_NUMBER):
        assert good.total > verifier.score(SOURCE, bad).total
    assert verifier.score(SOURCE, DROPPED_NUMBER).details["missing"]
    assert verifier.score(SOURCE, WRONG_NUMBER).details["unsupported"] == [(16.0, "mm")]


def test_copy_of_source_is_not_best(verifier):
    ranked = verifier.rank(SOURCE, [SOURCE, GOOD, WRONG_NUMBER])
    assert ranked[0][1] == GOOD


def test_entailment_uses_injected_scorer():
    low = Verifier(entail_fn=lambda p, hs: [0.1] * len(hs))
    assert low.entailment(SOURCE, GOOD) == pytest.approx(0.1)
    assert low.entailment(SOURCE, "") == 0.0


@pytest.mark.skipif(not os.environ.get("RUN_NLI"), reason="set RUN_NLI=1 to download/run the NLI model")
def test_real_nli_separates_supported_from_contradicted():
    v = Verifier()
    premise = "There is no pleural effusion. The heart is normal in size."
    support, contra = v.entail_fn(premise, ["The heart is normal.", "There is a large pleural effusion."])
    assert support > 0.5 > contra


def test_entailment_takes_best_support_over_source_sentences():
    seen = []

    def spy(premise, hypotheses):
        seen.append(premise)
        # only the single sentence "There is no pleural effusion." supports the hypothesis
        return [0.95 if premise == "There is no pleural effusion." else 0.1] * len(hypotheses)

    v = Verifier(entail_fn=spy)
    src = "The heart is normal in size. There is no pleural effusion. The lungs are clear."
    assert v.entailment(src, "You have no fluid around your lungs.") == pytest.approx(0.95)
    assert len(seen) == 4  # whole source + 3 source sentences


def test_parenthetical_glosses_are_not_scored():
    got = []
    v = Verifier(entail_fn=lambda p, hs: got.extend(hs) or [0.9] * len(hs))
    v.entailment("No pleural effusion.", "There is no fluid around the lungs (pleural effusion).")
    assert set(got) == {"There is no fluid around the lungs."}


def kinds(report, i=0):
    return {f["kind"]: f["terms"] for f in report["sentences"][i]["flags"]}


def test_explain_agrees_with_score_and_entailment():
    v = Verifier(entail_fn=lambda p, hs: [0.8] * len(hs))
    clean = GOOD.replace("a small spot", "a spot")  # "small" would be flagged as added severity
    e = v.explain(SOURCE, clean)
    s = v.score(SOURCE, clean)
    assert e["score"]["total"] == pytest.approx(s.total) and e["score"]["entail"] == pytest.approx(v.entailment(SOURCE, clean))
    assert e["sentences"][0]["text"].startswith("You have a spot")
    assert all(x["flags"] == [] for x in e["sentences"])  # nothing to flag
    assert e["summary"]["dropped_levels"] == []


def test_explain_flags_wrong_number_side_severity_and_hedge():
    v = Verifier(entail_fn=lambda p, hs: [0.9] * len(hs))
    assert kinds(v.explain("A 6 mm nodule.", "You have a 16 mm nodule.")) == {"wrong number": ["16 mm"]}
    assert kinds(v.explain("Effusion on the left.", "Fluid on the right.")) == {"wrong side": ["right"]}
    assert kinds(v.explain("A 5.4 cm nodule.", "A small nodule, 5.4 cm.")) == {"added severity": ["small"]}
    assert kinds(v.explain("No pleural effusion.", "There might be no fluid.")) == {"hedge changed": ["might be"]}


def test_explain_same_hedge_level_is_not_flagged_and_dropped_level_is_reported():
    v = Verifier(entail_fn=lambda p, hs: [0.9] * len(hs))
    same = v.explain("This may represent infection.", "This could be an infection.")
    assert same["sentences"][0]["flags"] == [] and same["sentences"][0]["level"] == "possible"
    dropped = v.explain("This may represent infection.", "This is an infection.")
    assert dropped["summary"]["dropped_levels"] == ["possible"]


def test_explain_flags_unsupported_sentence():
    v = Verifier(entail_fn=lambda p, hs: [0.1 if "tumor" in h else 0.9 for h in hs])
    e = v.explain("The lungs are clear.", "Your lungs are clear. There is a tumor.")
    assert kinds(e, 0) == {} and kinds(e, 1) == {"unsupported": []}


def word_overlap_entail(premise, hypotheses):
    have = set(premise.lower().replace(".", "").replace(",", "").split())
    return [1.0 if set(h.lower().replace(".", "").replace(",", "").split()) <= have else 0.0 for h in hypotheses]


def test_key_sentences_skip_plain_normals():
    from src.verify import key_sentences

    src = ("FINDINGS: The heart size is normal. No pleural effusion. A 6 mm nodule in the right lower lobe. "
           "The lungs are clear. IMPRESSION: Right lower lobe nodule, possibly infectious. No acute disease. "
           "Recommend follow-up CT in 3 months.")
    assert key_sentences(src) == ["A 6 mm nodule in the right lower lobe.",
                                  "Right lower lobe nodule, possibly infectious.",
                                  "Recommend follow-up CT in 3 months."]


def test_coverage_drops_when_the_impression_or_recommendation_is_left_out():
    v = Verifier(entail_fn=word_overlap_entail)
    full = "The right lower lobe nodule, possibly infectious. Recommend follow-up CT in 3 months."
    src = "FINDINGS: Nodule. IMPRESSION: Right lower lobe nodule, possibly infectious. Recommend follow-up CT in 3 months."
    assert v.score(src, full).coverage == 1.0
    partial = v.score(src, "The right lower lobe nodule, possibly infectious.")
    assert partial.coverage == 0.5 and partial.total < v.score(src, full).total
    assert [k for k, p in v.coverage(src, "The right lower lobe nodule, possibly infectious.") if p == 0] == [
        "Recommend follow-up CT in 3 months."]


def test_source_without_key_sentences_has_full_coverage_and_explain_lists_omissions():
    v = Verifier(entail_fn=word_overlap_entail)
    assert v.score("FINDINGS: The lungs are clear. IMPRESSION: No acute disease.", "Your lungs look fine.").coverage == 1.0
    out = v.explain("IMPRESSION: Right lower lobe nodule. Recommend CT in 3 months.", "A nodule was seen.")
    assert out["summary"]["possibly_omitted"] == ["Right lower lobe nodule.", "Recommend CT in 3 months."]
    assert out["score"]["coverage"] == 0.0


def test_explain_flags_new_checks():
    v = Verifier(entail_fn=always_entailed)
    kinds = lambda e: {f["kind"] for s in e["sentences"] for f in s["flags"]}  # noqa: E731
    e = v.explain("A 6 mm nodule in the right lower lobe. Scarring left greater than right.",
                  "A 6 mm spot in the left lung. The left lung is larger than the right.")
    assert {"number on wrong side", "added comparison"} <= kinds(e)
    assert e["summary"]["misplaced_numbers"] == ["6 mm"] and e["summary"]["wrong_comparisons"] == ["larger"]
