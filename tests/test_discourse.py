from src.discourse import parse_report

TEXT = (
    "FINDINGS: There is a 6 mm nodule in the right lower lobe. No pleural effusion. "
    "A CT scan could be performed for further evaluation. "
    "IMPRESSION: Right lower lobe nodule, possibly infectious. Recommend follow-up CT in 3 months."
)


def test_roles_and_certainty():
    r = parse_report(TEXT)
    roles = [(u.role, u.certainty) for u in r.units]
    assert roles == [
        ("finding", "definite"), ("finding", "definite"), ("recommendation", "definite"),
        ("impression", "possible"), ("recommendation", "definite"),
    ]
    assert r.units[0].numbers == [(6.0, "mm")] and r.units[4].numbers == [(3.0, "month")]


def test_relations():
    edges = set(parse_report(TEXT).edges)
    assert (4, "summarizes", 1) in edges    # impression -> nodule finding
    assert (5, "motivated_by", 4) in edges  # recommendation -> impression


def test_empty_findings_section():
    r = parse_report("FINDINGS: IMPRESSION: Stable cardiomegaly. No pneumothorax.")
    assert [u.role for u in r.units] == ["impression", "impression"]


def test_text_without_headers_is_all_findings():
    r = parse_report("Muscle cramps are common. They may be caused by heat.")
    assert [u.role for u in r.units] == ["finding", "finding"]
    assert r.units[1].certainty == "possible"
