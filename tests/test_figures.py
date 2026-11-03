from pathlib import Path

import pytest

from src.figdata import parse_auc, parse_summary

RES = Path(__file__).resolve().parent.parent / "results"


def test_parse_summary_rows_and_auc_table():
    md = ("# Plain LLM vs best-of-N (final, 120 reports)\n\n| metric | plain LLM | best-of-N | difference |\n|---|---|---|---|\n"
          "| any error H/N/F (labeled) | 0.81 | 0.68 | -0.12 (-0.21 to -0.04) |\n| reading grade (FK) | 10.01 | 10.59 | +0.58 (-0.07 to +1.21) |\n\n"
          "| score vs label | AUC | positives |\n|---|---|---|\n| total vs any H/N/F error | 0.81 | 97 |\n")
    got = parse_summary(md)
    assert got["reports"] == 120
    assert got["metrics"]["any error H/N/F (labeled)"] == {"plain": 0.81, "best": 0.68, "diff": -0.12, "lo": -0.21, "hi": -0.04}
    assert got["metrics"]["reading grade (FK)"]["hi"] == 1.21
    assert got["auc_plain"]["total vs any H/N/F error"] == {"auc": 0.81, "positives": 97}


def test_parse_auc_sections():
    txt = ("== dev (smoke run, baseline prompt): n=20, errored=13, clean=7\n"
           "  AUC total vs any error   0.68  (95% CI 0.43-0.93, positives=13)\n"
           "== set 3 (Qwen2.5-3B outputs, labeled blind, not used for tuning): n=40, errored=30, clean=10\n"
           "  AUC total vs any error   0.55  (95% CI 0.34-0.77, positives=30)\n")
    got = parse_auc(txt)
    assert got["dev (smoke run, baseline prompt)"]["checks"]["total vs any error"] == {"auc": 0.68, "lo": 0.43, "hi": 0.93, "positives": 13}
    assert got["set 3 (Qwen2.5-3B outputs, labeled blind, not used for tuning)"]["n"] == 40


@pytest.mark.skipif(not (RES / "final_summary.md").exists(), reason="results not present")
def test_real_result_files_parse_with_the_expected_rows():
    s = parse_summary((RES / "final_summary.md").read_text(encoding="utf-8"))
    for name in ("any error H/N/F (labeled)", "unsupported content (labeled)", "hedge error (labeled)",
                 "number/side error (labeled)", "key finding left out (labeled)", "reading grade (FK)", "simplicity"):
        assert name in s["metrics"], name
    assert len(s["auc_plain"]) == 5
    for f in ("verifier_auc_before.txt", "verifier_auc_after.txt"):
        sets = parse_auc((RES / f).read_text(encoding="utf-8"))
        assert sum("total vs any error" in v["checks"] for v in sets.values()) >= 5


FIG = Path(__file__).resolve().parent.parent / "figures"


@pytest.mark.skipif(not FIG.exists(), reason="figures not generated")
def test_figures_index_matches_the_files_on_disk():
    import re
    index = (FIG / "README.md").read_text(encoding="utf-8")
    listed = set()
    for cell in re.findall(r"^\| `([^|]+?)` \|", index, re.M):
        listed.update(c.strip("` ") for c in cell.split("`, `"))
    for folder in ("demo", "diagrams", "charts"):
        on_disk = {p.stem for p in (FIG / folder).iterdir() if p.suffix in (".png", ".svg", ".pdf")}
        for stem in on_disk:
            assert any(stem == name or (name.endswith("*") and stem.startswith(name[:-1])) for name in listed), f"{folder}/{stem} not in figures/README.md"
    for name in listed:
        if name.endswith("*"):
            assert list((FIG / "demo").glob(name[:-1] + "*.png")), name
        else:
            assert any((FIG / f).glob(name + ".png") for f in ("demo", "diagrams", "charts")), name
