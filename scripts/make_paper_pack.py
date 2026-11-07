"""Collect the figures and tables recommended for the paper into paper_pack/ (numbered, ready to drop in).

    .venv/Scripts/python scripts/make_paper_pack.py

Copies from figures/ (run make_figures.py and capture_screenshots.py first) and writes tables.md from results/.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.figdata import parse_auc, parse_summary  # noqa: E402

FIG, RES, OUT = ROOT / "figures", ROOT / "results", ROOT / "paper_pack"

# (new name, source under figures/, role in the paper)
MAIN = [("fig1-pipeline.png", "diagrams/pipeline.png", "Method overview"),
        ("fig2-verifier-components.png", "diagrams/verifier-components.png", "Method: what the verifier checks and its weights"),
        ("fig3-demo.png", "demo/02-full-ui-example.png", "The demo (system figure)"),
        ("fig4-error-rates.png", "charts/error-rates.png", "Main result: labeled error rates, plain vs best-of-N"),
        ("fig5-verifier-auc.png", "charts/verifier-auc.png", "Verifier AUC per set, before and after the new checks"),
        ("fig6-auc-plain-outputs.png", "charts/auc-plain-outputs.png", "Verifier components on the plain outputs (not circular)"),
        ("fig7a-example-plain-draft.png", "demo/14a-hedge-plain-draft.png", "Qualitative example: plain draft with flags"),
        ("fig7b-example-checked-draft.png", "demo/14b-hedge-checked-draft.png", "Qualitative example: checked draft"),
        ("fig7c-flag-reason.png", "demo/13-flag-tooltip-left_right.png", "Qualitative example: a flag and its reason"),
        ("fig8-data-and-evaluation.png", "diagrams/data-and-evaluation.png", "Datasets and evaluation sets (or appendix)")]
OPTIONAL = [("opt-readability.png", "charts/readability.png", "Limitation: checked drafts are not simpler"),
            ("opt-circular-vs-labeled.png", "charts/circular-vs-labeled.png", "Why verifier-scored gains are circular"),
            ("opt-error-types.png", "diagrams/error-types.png", "Labeling scheme (illustrative examples)")]


def pick(sets, prefix):
    return next(v for k, v in sets.items() if k.startswith(prefix))


def tables() -> str:
    s = parse_summary((RES / "final_summary.md").read_text(encoding="utf-8"))
    m, n = s["metrics"], s["reports"]
    out = ["# Tables for the paper", "", "All error labels were assigned blind by Claude (an AI), not by humans. CIs are 95% paired bootstrap.", "",
           f"## Table 1. Plain draft vs best-of-N on {n} unseen reports (labeled, independent of the verifier)", "",
           "| Error | Plain | Best-of-N | Difference (95% CI) |", "|---|---|---|---|"]
    for name, key in (("Any error (H, N or F)", "any error H/N/F (labeled)"), ("Unsupported content (F)", "unsupported content (labeled)"),
                      ("Hedge level changed (H)", "hedge error (labeled)"), ("Number or side wrong (N)", "number/side error (labeled)"),
                      ("Key finding left out (O)", "key finding left out (labeled)")):
        k = m[key]
        out.append(f"| {name} | {k['plain']:.2f} | {k['best']:.2f} | {k['diff']:+.2f} ({k['lo']:+.2f} to {k['hi']:+.2f}) |")
    out += ["", "Readability (lower reading grade is easier; higher simplicity is simpler):", "", "| Measure | Plain | Best-of-N | Difference (95% CI) |", "|---|---|---|---|"]
    for name, key in (("Reading grade (Flesch-Kincaid)", "reading grade (FK)"), ("Simplicity score", "simplicity")):
        k = m[key]
        out.append(f"| {name} | {k['plain']:.2f} | {k['best']:.2f} | {k['diff']:+.2f} ({k['lo']:+.2f} to {k['hi']:+.2f}) |")
    out += ["", "Verifier-scored rows are circular for best-of-N (the verifier chose the draft), so they are not shown here;",
            "see results/final_summary.md.", "",
            "## Table 2. Verifier AUC (total score vs any labeled error), before and after the comparison, number-side and omission checks", "",
            "| Set | n | Before (95% CI) | After (95% CI) |", "|---|---|---|---|"]
    before = parse_auc((RES / "verifier_auc_before.txt").read_text(encoding="utf-8"))
    after = parse_auc((RES / "verifier_auc_after.txt").read_text(encoding="utf-8"))
    for prefix, label in (("dev", "Dev"), ("test", "Set 1"), ("fresh set 2", "Set 2"), ("set 3", "Set 3 (3B outputs)"), ("dev+test combined", "Dev + set 1")):
        b, a = pick(before, prefix), pick(after, prefix)
        cb, ca = b["checks"]["total vs any error"], a["checks"]["total vs any error"]
        out.append(f"| {label} | {a['n']} | {cb['auc']:.2f} ({cb['lo']:.2f}-{cb['hi']:.2f}) | {ca['auc']:.2f} ({ca['lo']:.2f}-{ca['hi']:.2f}) |")
    out += ["", "AUC 0.5 is chance. Set 3 is not used for tuning and its AUC dropped; CIs are wide.", "",
            f"## Table 3. Verifier components on the {n} plain outputs (not circular)", "", "| Score vs label | AUC | Error cases |", "|---|---|---|"]
    for name, k in s["auc_plain"].items():
        out.append(f"| {name} | {k['auc']:.2f} | {k['positives']} |")
    out += ["", "Omission (coverage vs O) has only 5 error cases: weak evidence.", ""]
    return "\n".join(out)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "figures").mkdir(parents=True)
    (OUT / "optional").mkdir()
    for group, folder in ((MAIN, "figures"), (OPTIONAL, "optional")):
        for new, src, _ in group:
            shutil.copy2(FIG / src, OUT / folder / new)
    for new, src, _ in MAIN + OPTIONAL:                       # vector versions where they exist
        pdf = (FIG / src).with_suffix(".pdf")
        if pdf.exists():
            folder = "figures" if (new, src, _) in MAIN else "optional"
            shutil.copy2(pdf, OUT / folder / Path(new).with_suffix(".pdf"))
    (OUT / "tables.md").write_text(tables(), encoding="utf-8")
    rows = ["| File | Role |", "|---|---|"] + [f"| `figures/{n}` | {r} |" for n, _, r in MAIN] + [f"| `optional/{n}` | {r} |" for n, _, r in OPTIONAL]
    readme = (ROOT / "scripts" / "paper_pack_README.md").read_text(encoding="utf-8").replace("{{FILES}}", "\n".join(rows))
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    print("paper_pack:", len(list(OUT.rglob("*.*"))), "files")


if __name__ == "__main__":
    main()
