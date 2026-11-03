from src.numbers import compare, extract, extract_source


def test_extract_units_and_normalisation():
    assert extract("a 6 mm nodule, 1.5 cm lesion, EF 45%") == [(6.0, "mm"), (15.0, "mm"), (45.0, "%")]
    assert extract("follow-up in three months") == [(3.0, "month")]
    assert extract("53 Hounsfield units") == [(53.0, "hu")]


def test_list_markers_and_bare_numbers():
    assert extract_source("1. Normal heart. 2. Nodule at XXXX 7 XXXX.") == [(7.0, None)]


def test_cm_and_mm_are_equivalent():
    assert compare("a 6 mm nodule", "a 0.6 cm nodule")["score"] == 1.0


def test_wording_of_units_is_flexible():
    assert compare("nodule measuring 13 mm", "measures about 13 millimeters")["score"] == 1.0


def test_missing_number_detected():
    r = compare("nodule 6 mm, previously 4 mm", "a nodule of 6 mm")
    assert r["missing"] == [(4.0, "mm")] and r["unsupported"] == [] and r["score"] < 1


def test_invented_number_detected():
    r = compare("a nodule at XXXX 7 XXXX", "a 7 mm x 7 mm nodule seen 12 hours ago")
    assert (12.0, "hour") in r["unsupported"]  # 7 mm matches the bare source 7; 12 hours does not


def test_changed_number_is_both_missing_and_unsupported():
    r = compare("nodule 24 mm", "nodule 42 mm")
    assert r["missing"] == [(24.0, "mm")] and r["unsupported"] == [(42.0, "mm")] and r["score"] == 0.0


def test_no_numbers_anywhere_scores_one():
    assert compare("The lungs are clear.", "Your lungs look clear.")["score"] == 1.0
    assert compare("The lungs are clear.", "Your lungs are 5 cm clear.")["score"] == 0.0


def test_laterality_swap_is_penalised():
    r = compare("Mild blunting of the left costophrenic recess.", "Some fluid at the bottom right side of the lungs.")
    assert r["wrong_sides"] == {"right"} and r["score"] < 1
    assert compare("Left effusion.", "There is fluid on the left.")["score"] == 1.0
    assert compare("Bilateral effusions.", "Fluid around both lungs.")["score"] == 1.0


def test_severity_inflation_is_penalised():
    assert compare("Moderate cardiac failure.", "Severe cardiac failure.")["wrong_qualifiers"] == {"high"}
    assert compare("A 5.4 cm thyroid nodule.", "A small thyroid nodule, 5.4 cm.")["wrong_qualifiers"] == {"low"}
    assert compare("Mild cardiomegaly.", "The heart is slightly enlarged.")["wrong_qualifiers"] == set()


def test_negated_qualifier_is_ignored():
    assert compare("No pleural effusion.", "No significant fluid around the lungs.")["score"] == 1.0


def test_right_and_left_idioms_are_not_sides():
    from src.numbers import sides

    assert sides("You don't have any serious problems right now.") == set()
    assert sides("Everything is all right and nothing is left to worry about.") == set()
    assert sides("Fluid on the right.") == {"right"}
    assert sides("A nodule in the right lower lobe, right now stable.") == {"right"}
    assert compare("Effusion on the left.", "You have no serious problems right now. Fluid on the left.")["score"] == 1.0


def test_comparison_direction_is_normalised():
    from src.numbers import comparisons

    a = comparisons("Scarring, left greater than right.")[0]
    b = comparisons("Scarring, right less than left.")[0]
    assert (a["bigger"], a["smaller"]) == (b["bigger"], b["smaller"]) == ("left", "right")
    assert comparisons("No nodule larger than 5 mm. Less than 1 cm.") == []  # a measurement limit is not a comparison


def test_added_or_reversed_comparison_is_penalised():
    from src.numbers import wrong_comparisons

    src = "Chronic appearing left greater than right lung base scarring."
    # the known miss: scarring severity became lung size
    assert wrong_comparisons(src, "The left lung looks larger than the right.") == ["larger"]
    assert compare(src, "The left lung looks larger than the right.")["score"] < 1
    assert wrong_comparisons(src, "The scarring is worse on the right than the left.") == ["worse"]
    assert wrong_comparisons(src, "The scarring is worse on the left than the right.") == []
    assert wrong_comparisons("No change.", "Everything looks better than before.") == ["better"]
    assert wrong_comparisons("Heart is larger than before.", "The heart is bigger than on the last scan.") == []


def test_comparison_inside_a_gloss_is_ignored():
    assert compare("Hyperinflation.", "Hyperinflation (lungs holding more air than usual).")["score"] == 1.0


def test_number_attached_to_the_other_side_is_penalised():
    from src.numbers import misbound_numbers

    src = "A 6 mm nodule in the right lower lobe. The left lung is clear."
    assert misbound_numbers(src, "A 6 mm spot in your left lung.") == [(6.0, "mm")]
    assert misbound_numbers(src, "A 6 mm spot in your right lung.") == []
    assert misbound_numbers(src, "A 6 mm spot was seen.") == []          # no side stated: nothing to contradict
    assert compare(src, "A 6 mm spot in your left lung.")["score"] < 1
