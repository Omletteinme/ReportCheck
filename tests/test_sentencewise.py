import pytest

from src.discourse import parse_report
from src.generate import sentence_prompt
from src.glossary import find_terms
from src.sentencewise import assemble, clean, generate_candidates, rejection, simplify, word_changes

SRC = "There is no pleural effusion or pneumothorax."                 # a sentence that can be rewritten safely
GOOD = "No fluid around the lungs or collapsed lung on X-ray."
NODULE = "There is a 6 mm nodular opacity in the right lower lobe."    # a sentence with a number and a side
POSSIBLE = "There is possibly a 6 mm nodular opacity in the right lower lobe."
SOURCE = (
    "FINDINGS: There is no pleural effusion or pneumothorax. There is a 6 mm nodular opacity in the right lower lobe. "
    "Cardiomediastinal contours are within normal limits. "
    "IMPRESSION: Right lower lobe nodule, possibly infectious, though neoplasm cannot be excluded."
)


def sure(premise, hypotheses):
    return [0.95] * len(hypotheses)


def unsure(premise, hypotheses):
    return [0.1] * len(hypotheses)


class FakeGenerator:
    """Answers each prompt by the sentence it contains: `by_sentence` maps source sentence -> list of rewrites."""

    def __init__(self, by_sentence):
        self.by_sentence = by_sentence
        self.prompts = []

    def generate(self, prompt, n=1, temperature=0.0, max_new_tokens=300):
        self.prompts.append(prompt)
        sentence = prompt.split("SENTENCE: ")[-1].strip()
        rewrites = self.by_sentence.get(sentence, [])
        return rewrites[:1] if temperature == 0 else rewrites[1:]


def test_good_rewrite_is_accepted():
    assert rejection(SRC, GOOD, sure) is None


@pytest.mark.parametrize("bad, why", [
    ("There is a 16 mm nodular opacity in the right lower lobe.", "number"),
    ("There is a 6 mm nodular opacity in the left lower lobe.", "side"),
    ("There is a 6 mm nodular opacity in the lower lobe.", "side dropped"),
    ("There is a 6 mm nodular opacity in the right lower lobe (a lung section).", "parenthesis"),
    ("There is a 6 mm nodular opacity in the right lower lobe, nothing to worry about.", "added"),
    ("There is a 6 mm nodular opacity in the right lower lobe. See your doctor.", "added"),
    ("There is a 6 mm nodular opacity in the right lower lobe and", "cut off"),
    (POSSIBLE, "certainty"),
    ("There is a 6 mm nodular opacity near the right lower lobe cavity.", "new word"),
    ("There is a 6 mm round spot in the right lower lung.", "dropped word"),
    ("", "empty"),
])
def test_unsafe_rewrites_are_rejected(bad, why):
    reason = rejection(NODULE, bad, sure)
    assert reason and why in reason


def test_certainty_dropped_or_negation_flipped_is_rejected():
    assert "certainty" in rejection(POSSIBLE, "There is a 6 mm nodular opacity in the right lower lobe.", sure)
    assert rejection("There is no pneumothorax in the right lung.", "There is a pneumothorax in the right lung.", sure) == "negation changed"


def test_a_changed_medical_word_is_rejected_and_a_glossary_replacement_is_not():
    src = "There is consolidation in the right lower lobe."
    assert word_changes(src, "There is thickening in the right lower lobe.").startswith(("dropped word", "new word"))
    assert word_changes(SRC, GOOD) is None  # "pleural effusion" -> "fluid around the lungs" uses the reviewed wording
    assert "dropped word" in word_changes(SRC, "No abnormal findings.")


def test_new_words_must_come_from_the_source_the_glossary_or_the_safe_list():
    assert "new word" in word_changes(SRC, "No fluid around the lungs or collapsed lung with air bubbles.")


def test_rewrite_that_is_not_simpler_is_rejected():
    assert rejection(NODULE, NODULE, sure) == "not simpler"


def test_nli_must_support_the_rewrite_in_both_directions():
    assert rejection(SRC, GOOD, unsure) == "meaning not supported"
    only_forward = lambda premise, hs: [0.95] if premise == SRC else [0.1]  # noqa: E731
    assert rejection(SRC, GOOD, only_forward) == "content dropped"


def test_find_terms_returns_each_glossary_term_once_with_its_plain_wording():
    found = {t["term"]: t["plain"] for t in find_terms("Pleural effusion and pleural effusions, and a pneumothorax.")}
    assert found["pleural effusion"] == "fluid collecting around the lungs" and "pneumothorax" in found and len(found) == 2


def test_clean_strips_quotes_and_newlines():
    assert clean('  "There is a spot.\nIt is small." ') == "There is a spot. It is small."


def test_sentence_prompt_has_the_sentence_its_neighbours_and_the_rules():
    unit = parse_report(SOURCE).units[1]
    prompt = sentence_prompt(unit, "before text", "after text")
    assert prompt.endswith("SENTENCE: " + unit.text)
    assert "Previous sentence: before text" in prompt and "Next sentence: after text" in prompt
    assert "no parentheses" in prompt and "NUMBERS: 6 mm" in prompt and "CERTAINTY: definite" in prompt


def test_sentence_prompt_lists_the_approved_plain_wording_for_terms_in_the_sentence():
    prompt = sentence_prompt(parse_report(SOURCE).units[0])
    assert "pleural effusion = fluid collecting around the lungs" in prompt
    assert "Approved plain wording" not in sentence_prompt(parse_report("The patient arrived on time today.").units[0])


def test_generate_candidates_skips_xxxx_and_short_sentences():
    source = f"{NODULE} No pneumothorax. The XXXX is unremarkable today."
    gen = FakeGenerator({NODULE: [GOOD, GOOD, "Another spot."]})
    assert generate_candidates(gen, source) == [[GOOD, "Another spot."], [], []]
    assert len(gen.prompts) == 2  # greedy and sampled for the one rewritable sentence only


def test_assemble_keeps_every_source_sentence_in_order_and_falls_back():
    units = [u.text for u in parse_report(SOURCE).units]
    assert len(units) == 4
    result = assemble(SOURCE, [[GOOD], [POSSIBLE], [], ["It may be an infection or a tumor."]], sure)
    assert [u["source"] for u in result["units"]] == units
    assert result["units"][0]["status"] == "rewritten" and result["units"][0]["text"] == GOOD
    for kept in result["units"][1:]:
        assert kept["status"] == "kept" and kept["text"] == kept["source"] and kept["reason"]
    assert result["text"] == " ".join([GOOD] + units[1:])
    assert (result["rewritten"], result["total"]) == (1, 4)


def test_assemble_never_uses_a_failing_rewrite_even_when_it_is_the_only_one():
    result = assemble(SOURCE, [[], [POSSIBLE], [], []], sure)
    assert result["units"][1]["status"] == "kept" and "certainty" in result["units"][1]["reason"]
    assert result["text"].count(NODULE) == 1


def test_assemble_picks_the_simplest_passing_rewrite():
    shorter = "No fluid around the lungs or collapsed lung."
    result = assemble(SOURCE, [[GOOD, shorter], [], [], []], sure)
    assert result["units"][0]["status"] == "rewritten" and result["units"][0]["text"] in (GOOD, shorter)


def test_assemble_rejects_wrong_candidate_count():
    with pytest.raises(ValueError):
        assemble(SOURCE, [[GOOD]], sure)


def test_simplify_end_to_end_with_a_fake_generator():
    gen = FakeGenerator({SRC: [GOOD, POSSIBLE]})
    result = simplify(gen, sure, SOURCE)
    assert result["units"][0]["text"] == GOOD
    assert result["units"][0]["candidates"] == [GOOD, POSSIBLE]
