import pytest

from src.hedge import certainty_profile, sentence_certainty

CASES = [
    ("This could be consistent with sarcoidosis.", "possible"),
    ("A subtle infiltrate cannot be excluded.", "possible"),
    ("Mild bibasilar airspace disease, probably atelectasis.", "likely"),
    ("Right upper lobe opacity, favoring scarring and/or granulomas.", "likely"),
    ("Patchy left lower lobe airspace disease, concerning for pneumonia.", "likely"),
    ("Degenerative changes possibly consistent with DISH.", "possible"),
    ("Lesion that is unlikely to represent a primary neoplasm.", "unlikely"),
    ("The heart is normal in size.", "definite"),
    # false positives found in the Phase 1 precision check
    ("Further evaluation with contrast-enhanced CT of the thorax could be performed.", "definite"),
    ("If this area does not resolve, further characterization may be warranted.", "definite"),
    ("Consistent with the patient's history of known pulmonary fibrosis.", "definite"),
    ("No focal consolidation to suggest pneumonia.", "definite"),
]


@pytest.mark.parametrize("sentence,expected", CASES)
def test_sentence_certainty(sentence, expected):
    assert sentence_certainty(sentence) == expected


def test_patient_language_is_detected_too():
    assert sentence_certainty("This finding might mean pneumonia.") == "possible"
    assert sentence_certainty("It seems like you had an infection.") == "likely"


def test_profile_skips_definite_sentences():
    text = "The heart is normal. A nodule may represent infection. Probably granulomatous disease."
    assert certainty_profile(text) == ["possible", "likely"]
