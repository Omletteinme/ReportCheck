import os

import pytest

from src.generate import Generator, build_prompt

TEXT = "FINDINGS: A 6 mm nodule in the right lower lobe. IMPRESSION: Nodule, possibly infectious. Recommend CT in 3 months."


def test_structured_prompt_carries_certainty_numbers_and_relations():
    p = build_prompt(TEXT)
    assert "certainty=possible" in p and "6 mm" in p and "3 month" in p
    assert "summarizes" in p and "motivated_by" in p
    assert "A 6 mm nodule in the right lower lobe." in p


def test_baseline_prompt_is_plain():
    p = build_prompt(TEXT, mode="baseline")
    assert p.endswith(TEXT) and "certainty=" not in p


def test_unknown_mode():
    with pytest.raises(ValueError):
        build_prompt(TEXT, mode="nope")


@pytest.mark.skipif(not os.environ.get("RUN_GPU"), reason="set RUN_GPU=1 to load the model")
def test_generator_samples_n_candidates():
    outs = Generator().generate(build_prompt(TEXT), n=3, temperature=0.7, max_new_tokens=60)
    assert len(outs) == 3 and all(outs)


def test_plain_mode_adds_only_the_mild_rule():
    plain, base = build_prompt(TEXT, "structured_plain"), build_prompt(TEXT, "structured")
    assert "Replace medical jargon" in plain and "Replace medical jargon" not in base
    assert plain.replace(plain[plain.index("- Use plain"):plain.index("- Only cover")], "") == base
    assert "12-year-old" not in plain
