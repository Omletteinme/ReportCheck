import re

import pytest

from src import numbers, plainrules
from src.hedge import hedges
from src.plainrules import NEGATION, load, meaning_changes, simplify, simplify_sentence


@pytest.mark.parametrize("source, expected", [
    ("No acute cardiopulmonary abnormality.", "No new problem in the heart or lungs."),
    ("Heart size is within normal limits.", "Heart size is normal."),
    ("Within normal limits.", "Normal."),
    ("There is no pleural effusion or pneumothorax.", "There is no fluid around the lungs or air leak around the lung."),
    ("There is a pleural effusion.", "There is fluid around the lungs."),
    ("Bilateral pleural effusions are present.", "Fluid around both lungs is present."),
    ("Small pleural effusions are noted.", "Small amount of fluid around the lungs is noted."),
    ("A pleural effusion is seen on the left.", "Fluid around the lungs is seen on the left."),
    ("Small pleural effusions.", "Small amount of fluid around the lungs."),
    ("There is no evidence of pneumonia.", "There is no sign of pneumonia."),
    ("The visualized osseous structures are intact.", "The visible bones are intact."),
    ("This may represent atelectasis.", "This may be partly collapsed lung."),
    ("Pulmonary vasculature is normal.", "Blood vessels of the lungs are normal."),
    ("Lungs are clear bilaterally.", "Lungs are clear on both sides."),
    ("Bilateral opacities.", "Bilateral opacities."),
])
def test_rewrites(source, expected):
    assert simplify_sentence(source)[0] == expected


def test_numbers_sides_and_unmatched_text_pass_through_unchanged():
    sentence = "A 6 mm nodule in the right lower lobe."
    assert simplify_sentence(sentence) == (sentence, [], [])


def test_a_swap_that_changes_meaning_falls_back_to_the_source(monkeypatch):
    bad = [(re.compile(r"right", re.I), "left", "right")]
    monkeypatch.setattr(plainrules, "load", lambda: bad)
    text, applied, problems = simplify_sentence("There is a nodule in the right lung.")
    assert text == "There is a nodule in the right lung." and applied == [] and problems == ["side"]


@pytest.mark.parametrize("source, rewrite, problem", [
    ("A 6 mm nodule.", "A 16 mm nodule.", "number"),
    ("Left lung opacity.", "Right lung opacity.", "side"),
    ("Small effusion.", "Large effusion.", "severity"),
    ("This may be a nodule.", "This is a nodule.", "certainty"),
    ("No effusion.", "An effusion.", "negation"),
])
def test_meaning_changes_names_the_problem(source, rewrite, problem):
    assert any(problem in p for p in meaning_changes(source, rewrite))


def test_simplify_a_whole_report_drops_section_labels_and_counts_changes():
    result = simplify("FINDINGS: Heart size is within normal limits. No pneumothorax. IMPRESSION: No acute cardiopulmonary abnormality.")
    assert result["text"] == "Heart size is normal. No air leak around the lung. No new problem in the heart or lungs."
    assert (result["changed"], result["total"]) == (3, 3)


def test_every_rule_keeps_the_meaning_words_of_its_pattern():
    """A rule may only introduce a negation, side, number, hedge or severity group that its own pattern already has."""
    for pattern, replacement, source in load():
        literal = re.sub(r"[\\()?:|]", " ", source)
        assert bool(NEGATION.search(replacement)) <= bool(NEGATION.search(literal)), source
        assert numbers.sides(replacement) <= numbers.sides(literal), source
        assert numbers.qualifier_groups(replacement) <= numbers.qualifier_groups(literal), source
        assert not re.search(r"\d", replacement.replace(r"\1", "")), source
        assert {lvl for _, lvl in hedges(replacement)} <= {lvl for _, lvl in hedges(literal)}, source
        assert re.compile(source)  # valid regex


def test_rules_are_ordered_specific_first():
    """A shorter rule listed above a longer one that contains it would make the longer rule unreachable."""
    rows = [(pattern, source) for pattern, _, source in load()]
    plain = [(p, s) for p, s in rows if not re.search(r"[\\()?:|]", s)]
    for i, (_, short) in enumerate(plain):
        for _, long_ in plain[i + 1:]:
            assert short not in long_.split() and f" {short} " not in f" {long_} " or short == long_, (short, long_)


def test_real_reports_get_simpler_and_almost_never_fall_back():
    from src.data import load_reports
    textstat = pytest.importorskip("textstat")
    reports = [r["text"] for r in load_reports().values() if r["source"] == "openi"][:300]
    if len(reports) < 100:
        pytest.skip("reports not present")
    results = [simplify(t) for t in reports]
    before = sum(textstat.flesch_kincaid_grade(t) for t in reports) / len(reports)
    after = sum(textstat.flesch_kincaid_grade(r["text"]) for r in results) / len(reports)
    kept = sum(bool(s["problems"]) for r in results for s in r["sentences"])
    total = sum(r["total"] for r in results)
    assert before - after >= 3 and kept / total < 0.01
