import re

from src import numbers
from src.glossary import gloss, gloss_sentences, load
from src.hedge import certainty_profile, hedges
from src.verify import Verifier, certainty_score

DRAFT = ("The pulmonary arteries are dilated. There is no pleural effusion or pneumothorax. "
         "Moderate hyperinflation of the lungs, which suggests obstructive pulmonary disease.")


def test_every_explanation_is_free_of_hedges_sides_severity_and_numbers():
    for e in load():
        text = e["plain"]
        assert not hedges(text), f"{e['term']}: hedge in explanation"
        assert not numbers.side_words(text), f"{e['term']}: side word"
        assert not numbers.qualifier_words(text), f"{e['term']}: severity word"
        assert not numbers.find_facts(text) and not re.search(r"\d", text), f"{e['term']}: number"
        assert 1 <= len(text.split()) <= 16 and "(" not in text and "," not in text


def test_glossary_has_no_duplicate_forms():
    forms = [f.lower() for e in load() for f in [e["term"], *e["variants"]]]
    assert len(forms) == len(set(forms))


def test_first_occurrence_only_and_longest_match_wins():
    out = gloss("There is a pleural effusion. A second pleural effusion is stable. Fluid effusion noted.")
    assert out.count("pleural effusion (fluid collecting around the lungs)") == 1
    assert "effusion (fluid collecting in a space around an organ)" not in out.split("A second")[0]  # not the generic one
    assert out.split("A second")[1].count("(") == 1  # only the generic "effusion" at the end gets its own gloss


def test_case_variants_and_plurals():
    s = gloss_sentences(["Pulmonary Arteries are dilated.", "Calcifications and a Granuloma."])
    assert s[0]["terms"] == ["pulmonary artery"] and s[0]["glossed"].startswith("Pulmonary Arteries (")
    assert s[1]["terms"] == ["calcification", "granuloma"]


def test_already_explained_or_parenthesized_terms_are_left_alone():
    s = gloss_sentences(["Pneumothorax (collapsed lung) is absent.", "Fluid (pleural effusion) is absent."])
    assert s[0]["glossed"] == s[0]["text"] and s[0]["terms"] == []
    assert s[1]["glossed"] == s[1]["text"]


def test_text_without_terms_is_unchanged_and_whole_word_only():
    assert gloss("Your heart looks normal.") == "Your heart looks normal."
    assert gloss("Cardiopulmonary findings.").startswith("Cardiopulmonary (relating to the heart and lungs)")
    assert gloss("A pulmonaryx word.") == "A pulmonaryx word."


def test_max_glosses_caps_explanations():
    out = gloss(DRAFT, max_glosses=1)
    assert out.count("(") == 1


def test_glossing_does_not_change_verifier_scores():
    seen = {"plain": [], "glossed": []}

    def spy(key):
        return lambda premise, hs: seen[key].extend(hs) or [0.9] * len(hs)

    source = ("FINDINGS: The pulmonary arteries are dilated. No pleural effusion or pneumothorax. "
              "IMPRESSION: Moderate hyperinflation, consistent with obstructive pulmonary disease.")
    glossed = gloss(DRAFT)
    assert glossed != DRAFT
    a, b = Verifier(entail_fn=spy("plain")).score(source, DRAFT), Verifier(entail_fn=spy("glossed")).score(source, glossed)
    assert seen["plain"] == seen["glossed"]  # same sentences reach the meaning check
    assert (a.entail, a.numbers, a.certainty) == (b.entail, b.numbers, b.certainty)
    assert certainty_profile(DRAFT) == certainty_profile(glossed) and certainty_score(source, DRAFT) == certainty_score(source, glossed)


def test_parts_rebuild_the_glossed_text_and_mark_explanations():
    s = gloss_sentences(["There is no pneumothorax."])[0]
    assert "".join(t for t, _ in s["parts"]) == s["glossed"] == "There is no pneumothorax (air outside the lung that can make it collapse)."
    assert [g for _, g in s["parts"]] == [False, True, False]


def test_annotate_keeps_explain_fields_and_adds_gloss_info():
    from src.glossary import annotate

    sentences = [{"text": "No pleural effusion.", "support": 0.9, "flags": []}]
    a = annotate(sentences)[0]
    assert a["support"] == 0.9 and a["flags"] == [] and a["gloss_terms"] == ["pleural effusion"]
    assert a["parts"][1] == {"t": " (fluid collecting around the lungs)", "gloss": True}
