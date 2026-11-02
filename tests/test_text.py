from src.text import split_sentences


def test_plain_sections_are_split():
    assert split_sentences("FINDINGS: Clear lungs. IMPRESSION: Normal. Recommend CT.") == [
        "Clear lungs.", "Normal.", "Recommend CT."]


def test_inline_bold_labels_keep_their_text():
    # regression: "**Findings:** text **Impression:** text" used to vanish as a fake bold heading
    out = split_sentences("**Findings:** The lungs appear clear. A nodule could be fat. **Impression:** Clear lungs.")
    assert out == ["The lungs appear clear.", "A nodule could be fat.", "Clear lungs."]


def test_headings_and_bullets():
    text = "### Patient Report\n**Radiology Report Summary**\n**Findings:**\n- Heart is normal.\n- No effusion.\n1. Nodule."
    assert split_sentences(text) == ["Heart is normal.", "No effusion.", "Nodule."]


def test_list_marker_does_not_split_sentence():
    assert split_sentences("1. Low lung volumes. 2. Mild congestion.") == ["Low lung volumes.", "Mild congestion."]
