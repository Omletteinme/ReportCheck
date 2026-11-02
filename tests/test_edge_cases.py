"""Edge cases, plus data-driven checks against the real and synthetic reports (skipped if the data is absent)."""
import json
from pathlib import Path

import pytest

from src.discourse import parse_report
from src.hedge import sentence_certainty
from src.numbers import compare, extract, sides
from src.text import split_sentences
from src.verify import certainty_score, simplicity_score

DATA = Path(__file__).resolve().parent.parent / "data"


def load(name):
    path = DATA / name
    if not path.exists():
        pytest.skip(f"{name} not present")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---- hedge: more wording, and negation / non-hedge look-alikes -------------------------------------------------
HEDGE_CASES = [
    ("Findings are suspicious for malignancy.", "likely"),
    ("Cannot rule out a small pneumothorax.", "possible"),
    ("Small pneumothorax is not ruled out.", "possible"),
    ("Could represent early pneumonia.", "possible"),
    ("Likely atelectasis.", "likely"),
    ("Pneumonia is unlikely.", "unlikely"),
    ("Not likely to represent infection.", "unlikely"),
    ("Findings are compatible with chronic bronchitis.", "likely"),
    ("The aorta is tortuous.", "definite"),
    ("There is a large right pleural effusion.", "definite"),
    ("No pneumothorax.", "definite"),
    ("", "definite"),
]


@pytest.mark.parametrize("sentence,expected", HEDGE_CASES)
def test_more_hedge_cases(sentence, expected):
    assert sentence_certainty(sentence) == expected


# ---- numbers: units, ranges, formatting ------------------------------------------------------------------------
def test_decimal_comma_and_spacing_variants():
    assert extract("a 6mm nodule") == [(6.0, "mm")]
    assert extract("a 6 MM nodule") == [(6.0, "mm")]
    assert extract("measures 1.2 cm") == [(12.0, "mm")]


def test_empty_and_numberless_text():
    assert extract("") == []
    assert compare("", "")["score"] == 1.0


def test_two_numbers_both_required():
    r = compare("nodules of 5 mm and 9 mm", "nodules of 5 mm")
    assert r["missing"] == [(9.0, "mm")] and r["score"] < 1


def test_number_repeated_in_output_counts_as_extra():
    # known behaviour: numbers are matched one-to-one, so restating a measurement is penalised (not free)
    r = compare("a 5 mm nodule", "a 5 mm nodule, yes a 5 mm nodule")
    assert r["unsupported"] == [(5.0, "mm")] and r["score"] < 1


def test_sides_cases():
    assert sides("Bilateral pleural effusions.") == {"left", "right"}  # bilateral = both sides
    assert sides("The heart is normal.") == set()
    assert sides("Left greater than right.") == {"left", "right"}


@pytest.mark.parametrize("src,out", [
    ("Right lower lobe opacity.", "A spot in the left lower part of the lung."),
    ("Left pleural effusion.", "Fluid around the right lung."),
])
def test_swapped_side_always_scores_below_one(src, out):
    assert compare(src, out)["score"] < 1


# ---- verify helpers --------------------------------------------------------------------------------------------
def test_certainty_score_penalises_added_and_dropped_hedges():
    src = "A nodule is possibly infectious."
    assert certainty_score(src, "The nodule is possibly an infection.") == 1.0
    assert certainty_score(src, "The nodule is an infection.") < 1.0
    assert certainty_score("The heart is normal.", "The heart may be normal.") < 1.0


def test_simplicity_never_negative_or_above_one():
    src = "Cardiomegaly with bibasilar atelectasis and small bilateral pleural effusions."
    for out in ("", "x", src, "Your heart is big and parts of both lungs are collapsed, with a little fluid."):
        assert 0.0 <= simplicity_score(src, out) <= 1.0


# ---- text / discourse ------------------------------------------------------------------------------------------
def test_empty_and_whitespace_input():
    assert split_sentences("") == [] and split_sentences("   \n  ") == []
    assert parse_report("").units == []


def test_repeated_section_label_keeps_every_sentence():
    # regression: report id 2415 restates FINDINGS inside the impression; the second block overwrote the first
    text = ("FINDINGS: The heart is enlarged. The lungs are clear. IMPRESSION: Cardiomegaly. "
            "FINDINGS: There is a small effusion. IMPRESSION: Small effusion.")
    got = [u.text for u in parse_report(text).units]
    assert got == split_sentences(text) and len(got) == 5
    assert [u.role for u in parse_report(text).units] == ["finding", "finding", "impression", "finding", "impression"]


def test_recommendation_role_and_motivated_by_edge():
    rep = parse_report("FINDINGS: A 12 mm nodule in the left upper lobe. IMPRESSION: Nodule. Recommend CT in 3 months.")
    rec = [u for u in rep.units if u.role == "recommendation"]
    assert len(rec) == 1 and any(e[1] == "motivated_by" and e[0] == rec[0].id for e in rep.edges)


# ---- data-driven: synthetic reports carry their own ground truth -----------------------------------------------
def test_extractors_recover_every_synthetic_ground_truth_fact():
    rows = load("synthetic.jsonl")
    assert len(rows) >= 50
    for r in rows:
        got = {f for u in parse_report(r["text"]).units for f in u.numbers}
        for n in r["meta"]["numbers"]:
            assert set(extract(n)) <= got, (r["id"], n)
        if r["meta"]["certainty"] != "definite":
            assert any(u.certainty == r["meta"]["certainty"] for u in parse_report(r["text"]).units), r["id"]


def test_synthetic_ids_unique_and_labeled_synthetic():
    rows = load("synthetic.jsonl")
    assert len({r["id"] for r in rows}) == len(rows)
    assert all(r["source"] == "synthetic" and r["id"].startswith("synth_") for r in rows)


# ---- data-driven: invariants over every real report ------------------------------------------------------------
def test_every_real_report_is_self_consistent():
    rows = load("reports.jsonl")
    assert len(rows) > 3000
    problems = []
    for r in rows:
        t = r["text"]
        if compare(t, t)["score"] != 1.0:
            problems.append(("numbers-self", r["id"]))
        if certainty_score(t, t) != 1.0:
            problems.append(("certainty-self", r["id"]))
        if len(parse_report(t).units) != len(split_sentences(t)):
            problems.append(("units", r["id"]))
    assert not problems, problems[:10]


def test_split_is_disjoint_and_ids_exist():
    split = json.loads((DATA / "split.json").read_text(encoding="utf-8")) if (DATA / "split.json").exists() else None
    if split is None:
        pytest.skip("split.json not present")
    ids = {str(r["id"]) for r in load("reports.jsonl") + load("synthetic.jsonl")}
    assert not set(split["train"]) & set(split["test"])
    assert set(split["train"]) | set(split["test"]) <= ids
