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
