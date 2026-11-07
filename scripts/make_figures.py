"""Diagrams (SVG + PNG) and result charts (PNG + PDF) for the paper, report and slides -> figures/.

    .venv/Scripts/python scripts/make_figures.py

Charts read their numbers from results/final_summary.md and results/verifier_auc_*.txt (src/figdata.py), never from
hand-typed values. Diagrams are plain SVG written here, so teammates can edit the .svg files directly.
PNG rendering of the SVGs uses Playwright with the installed Edge (pip install playwright, see requirements-figures.txt).
"""
import sys
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.figdata import parse_auc, parse_summary  # noqa: E402
from src.verify import WEIGHTS  # noqa: E402

OUT = ROOT / "figures"
RES = ROOT / "results"
INK, MUTED, LINE, CARD, ACCENT, GRAY = "#14171f", "#596173", "#d9dde5", "#f3f5f8", "#2453c4", "#8a93a3"
FOOT = "AI-labeled. Reports: public Open-i chest X-ray set."

plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 11, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "text.color": INK, "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name, footer=FOOT):
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.text(0.01, 0.005, footer, fontsize=8, color=MUTED, va="bottom")
    d = OUT / "charts"
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(d / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("saved charts/" + name, flush=True)


# ------------------------------------------------------------------ charts
def charts():
    summary = parse_summary((RES / "final_summary.md").read_text(encoding="utf-8"))
    m, n = summary["metrics"], summary["reports"]
    before = parse_auc((RES / "verifier_auc_before.txt").read_text(encoding="utf-8"))
    after = parse_auc((RES / "verifier_auc_after.txt").read_text(encoding="utf-8"))

    # 1 labeled error rates, plain vs best-of-N
    rows = [("Any error\n(hedge, number/side,\nunsupported)", "any error H/N/F (labeled)"), ("Unsupported\ncontent", "unsupported content (labeled)"),
            ("Hedge level\nchanged", "hedge error (labeled)"), ("Number or side\nwrong", "number/side error (labeled)"),
            ("Key finding\nleft out", "key finding left out (labeled)")]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    xs = range(len(rows))
    ax.bar([x - 0.2 for x in xs], [m[k]["plain"] for _, k in rows], 0.38, color=GRAY, label="Plain draft")
    ax.bar([x + 0.2 for x in xs], [m[k]["best"] for _, k in rows], 0.38, color=ACCENT, label="Best-of-N (checked draft)")
    for x, (_, k) in zip(xs, rows):
        ax.text(x, max(m[k]["plain"], m[k]["best"]) + 0.03, f"{m[k]['diff']:+.2f}\n({m[k]['lo']:+.2f} to {m[k]['hi']:+.2f})", ha="center", fontsize=8.5, color=MUTED)
        for dx, key in ((-0.2, "plain"), (0.2, "best")):
            ax.text(x + dx, m[k][key] / 2, f"{m[k][key]:.2f}", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    ax.set_xticks(list(xs), [r[0] for r in rows])
    ax.set_ylabel("Share of outputs with the error")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Labeled error rates on {n} unseen reports (difference with 95% CI above each pair; lower is better)", fontsize=10.5, loc="left")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "error-rates", FOOT + f" n = {n} reports, 240 outputs (202 distinct).")

    # 2 verifier AUC before vs after
    key = "total vs any error"
    names = [("dev", "Dev\n(n=20)"), ("test", "Set 1\n(n=40)"), ("fresh set 2", "Set 2\n(n=40)"), ("set 3", "Set 3, 3B outputs\n(n=40)"), ("dev+test combined", "Dev + set 1\n(n=60)")]

    def pick(sets, prefix):
        return next(v["checks"][key] for k, v in sets.items() if k.startswith(prefix))
    fig, ax = plt.subplots(figsize=(9, 4.4))
    for off, sets, color, label in ((-0.2, before, GRAY, "Before the new checks"), (0.2, after, ACCENT, "After (comparison, number-side, omission)")):
        vals = [pick(sets, p) for p, _ in names]
        ax.bar([i + off for i in range(len(names))], [v["auc"] for v in vals], 0.38, color=color, label=label,
               yerr=[[v["auc"] - v["lo"] for v in vals], [v["hi"] - v["auc"] for v in vals]], capsize=3, error_kw={"lw": 1, "ecolor": INK})
        for i, v in enumerate(vals):
            ax.text(i + off, 0.05, f"{v['auc']:.2f}", ha="center", color="white", fontsize=9, fontweight="bold")
    ax.axhline(0.5, color=MUTED, ls="--", lw=1)
    ax.text(-0.48, 0.515, "chance", color=MUTED, fontsize=8, ha="left")
    ax.set_xticks(range(len(names)), [t for _, t in names])
    ax.set_ylim(0, 1.2)
    ax.set_ylabel("AUC: total score vs any labeled error")
    ax.set_title("Can the verifier tell clean outputs from flawed ones? (bars: AUC, whiskers: 95% CI)", fontsize=10.5, loc="left")
    ax.legend(frameon=False, loc="upper left", ncol=2, bbox_to_anchor=(0, 1.0))
    save(fig, "verifier-auc")

    # 3 AUC per component on the plain outputs
    comp = [("Total score vs\nany error", "total vs any H/N/F error"), ("Certainty vs\nhedge error", "certainty vs H"), ("Numbers vs\nnumber/side error", "numbers vs N"),
            ("Entailment vs\nunsupported content", "entail vs F"), ("Coverage vs\nomission", "coverage vs O (omission)")]
    a = summary["auc_plain"]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    vals = [a[k]["auc"] for _, k in comp]
    bars = ax.bar(range(len(comp)), vals, 0.55, color=ACCENT)
    for b, (_, k) in zip(bars, comp):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015, f"{b.get_height():.2f}\n({a[k]['positives']} errors)", ha="center", fontsize=9)
    ax.axhline(0.5, color=MUTED, ls="--", lw=1)
    ax.set_xticks(range(len(comp)), [c[0] for c in comp])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("AUC (0.5 = chance)")
    ax.set_title(f"Verifier components on the {n} plain drafts it did not choose (not circular)", fontsize=10.5, loc="left")
    save(fig, "auc-plain-outputs", FOOT + " Omission has only 5 positive cases, so treat that bar as weak evidence.")

    # 4 readability
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.5, 3.8))
    g, s = m["reading grade (FK)"], m["simplicity"]
    for ax, k, title, ylab in ((a1, g, "Reading grade (Flesch-Kincaid, lower is easier)", "School grade"), (a2, s, "Simplicity score (higher is simpler)", "Score 0 to 1")):
        ax.bar([0, 1], [k["plain"], k["best"]], 0.55, color=[GRAY, ACCENT])
        for i, v in enumerate((k["plain"], k["best"])):
            ax.text(i, v + max(k["plain"], k["best"]) * 0.02, f"{v:.2f}", ha="center")
        ax.set_xticks([0, 1], ["Plain draft", "Checked draft"])
        ax.set_ylim(0, max(k["plain"], k["best"]) * 1.18)
        ax.set_title(title, fontsize=9.5, loc="left")
        ax.set_ylabel(ylab)
        ax.text(0.5, -0.28, f"difference {k['diff']:+.2f} (95% CI {k['lo']:+.2f} to {k['hi']:+.2f})", transform=ax.transAxes, ha="center", fontsize=8.5, color=MUTED)
    fig.suptitle("The checked drafts are not simpler to read", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    save(fig, "readability", "Reading grade by the textstat library. n = %d reports." % n)

    # 5 circular vs labeled gains (positive = better for the checked draft)
    items = [("Verifier total (circular)", m["verifier total"], 1, GRAY), ("Meaning (circular)", m["meaning (entailment)"], 1, GRAY),
             ("Certainty (circular)", m["certainty"], 1, GRAY), ("Numbers and sides (circular)", m["numbers/sides"], 1, GRAY),
             ("Fewer unsupported claims (labeled)", m["unsupported content (labeled)"], -1, ACCENT), ("Fewer hedge errors (labeled)", m["hedge error (labeled)"], -1, ACCENT),
             ("Fewer number/side errors (labeled)", m["number/side error (labeled)"], -1, ACCENT), ("Fewer errors of any kind (labeled)", m["any error H/N/F (labeled)"], -1, ACCENT)]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for i, (name, k, sign, color) in enumerate(items):
        d, lo, hi = (k["diff"], k["lo"], k["hi"]) if sign > 0 else (-k["diff"], -k["hi"], -k["lo"])
        ax.barh(i, d, color=color, height=0.55)
        ax.errorbar(d, i, xerr=[[d - lo], [hi - d]], color=INK, capsize=3, lw=1)
        ax.text(max(hi, d) + 0.01, i, f"{d + 0.0:+.2f}".replace("-0.00", "+0.00"), va="center", fontsize=9)
    ax.set_yticks(range(len(items)), [i[0] for i in items])
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_xlabel("Gain of the checked draft over the plain draft (95% CI); positive is better")
    ax.set_title("Gain of the checked draft: scored by the verifier (grey) and by labels (blue)", fontsize=10.5, loc="left")
    save(fig, "circular-vs-labeled", "Grey rows are scored by the same verifier that picked the draft, so they are circular. " + FOOT)


# ------------------------------------------------------------------ diagrams (SVG)
FONT = "Segoe UI, Arial, sans-serif"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.parts = w, h, []
        self.title = title

    def box(self, x, y, w, h, title, lines=(), fill=CARD, stroke=LINE, tcolor=INK, accent=False):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{ACCENT if accent else fill}" stroke="{stroke}" stroke-width="1.5"/>')
        tc = "#ffffff" if accent else tcolor
        self.parts.append(f'<text x="{x + 18}" y="{y + 34}" font-size="20" font-weight="600" fill="{tc}">{escape(title)}</text>')
        for i, ln in enumerate(lines):
            self.parts.append(f'<text x="{x + 18}" y="{y + 62 + 23 * i}" font-size="15.5" fill="{"#e8eefc" if accent else MUTED}">{escape(ln)}</text>')

    def arrow(self, x1, y1, x2, y2):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2 - 9}" y2="{y2}" stroke="{MUTED}" stroke-width="2"/>'
                          f'<path d="M{x2} {y2} l-11 -6 v12 z" fill="{MUTED}"/>')

    def text(self, x, y, s, size=15, color=MUTED, weight=400, anchor="start"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(s)}</text>')

    def render(self):
        body = "\n  ".join(self.parts)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" font-family="{FONT}">\n'
                f'  <title>{escape(self.title)}</title>\n  <rect width="{self.w}" height="{self.h}" fill="#ffffff"/>\n  {body}\n</svg>\n')


def diagram_pipeline():
    s = Svg(1900, 430, "Pipeline: report to checked patient draft")
    s.text(40, 54, "How a report becomes a checked patient draft", 28, INK, 600)
    steps = [("1  Report", ["Open-i report, pasted text,", "or a .txt / .docx / .pdf file"]),
             ("2  Parse", ["Hedge levels, numbers,", "left/right, severity words,", "finding / impression roles"]),
             ("3  Draft", ["Qwen2.5-1.5B-Instruct", "pretrained, not fine-tuned", "1 plain + 10 drafts (2 greedy,", "8 sampled)"]),
             ("4  Verify", ["Meaning (NLI), numbers,", "sides, hedge level,", "simplicity, coverage"]),
             ("5  Pick", ["Best draft that passes the", "hard checks (best-of-N)"]),
             ("6  Explain", ["Fixed 95-term glossary adds", "plain-language term notes", "(display only)"]),
             ("7  Show", ["3D body map, flagged words,", "findings explorer"])]
    w, gap, x0, y = 230, 40, 40, 110
    for i, (t, lines) in enumerate(steps):
        x = x0 + i * (w + gap)
        s.box(x, y, w, 170, t, lines, accent=(i == 3))
        if i:
            s.arrow(x - gap + 4, y + 85, x - 2, y + 85)
    s.text(40, 340, "The language model only writes drafts. The checker is our own code: it never edits a draft, it scores it and flags what changed.", 17, MUTED)
    s.text(40, 372, "No model was trained or fine-tuned. Steps 2, 4, 5 and 6 are rules plus a pretrained entailment model (DeBERTa NLI).", 17, MUTED)
    return s


def diagram_verifier():
    s = Svg(1900, 640, "Verifier components and weights")
    s.text(40, 54, "What the verifier checks in a draft (score 0 to 1, weights add to 1)", 28, INK, 600)
    comps = [("Meaning kept", "entail", ["Each draft sentence must be", "supported by the report (NLI)", "Catches: invented claims"]),
             ("Numbers and sides", "numbers", ["Numbers and units, left/right,", "severity words, comparisons,", "number tied to the right side"]),
             ("Certainty kept", "certainty", ["Hedge levels (unlikely < possible", "< likely < definite) stay the same", "Catches: 'may be' turned into 'is'"]),
             ("Plainer wording", "simplicity", ["Readability gain; zero for", "near-copies of the report", "(shown as Plainer wording)"]),
             ("Nothing left out", "coverage", ["Impression, recommendations and", "hedged or measured findings", "must still be stated"])]
    w, gap, x0, y = 330, 34, 40, 100
    for i, (t, key, lines) in enumerate(comps):
        x = x0 + i * (w + gap)
        s.box(x, y, w, 190, t, lines)
        s.text(x + 18, y + 176, f"weight {WEIGHTS[key]:.4f}".rstrip("0"), 17, ACCENT, 600)
        s.arrow(x + w // 2, y + 190, x + w // 2, y + 270) if False else None
    s.parts.append(f'<rect x="40" y="330" width="1810" height="70" rx="16" fill="{ACCENT}"/>')
    s.text(70, 374, "Total score = weighted sum of the five parts. Used to rank the drafts.", 21, "#ffffff", 600)
    s.box(40, 430, 1810, 150, "A draft can only be chosen if it also passes these hard checks",
          ["numbers and sides score is 1.0   |   certainty at least 0.75   |   meaning at least 0.7   |   simplicity at least 0.1",
           "If no draft passes, the highest total is shown and the page says so."])
    s.text(40, 614, "Source: src/verify.py (WEIGHTS) and src/bestofn.py (acceptable). The omission check is a soft score because the NLI model is noisy on paraphrases.", 14.5, MUTED)
    return s


def diagram_data():
    s = Svg(1900, 640, "Data and evaluation sets")
    s.text(40, 54, "Which reports were used for what", 28, INK, 600)
    s.box(40, 100, 420, 150, "Open-i chest X-ray reports", ["3,159 public, anonymised reports", "XXXX marks text removed by NLM"])
    s.box(40, 290, 420, 120, "50 synthetic reports", ["Template-written, labeled synthetic", "Unit tests only, in no result"])
    s.box(40, 450, 420, 120, "PLABA abstracts", ["749 plain-language abstracts", "Not used in the results"])
    s.arrow(460, 175, 560, 175)
    s.box(560, 100, 420, 150, "Split (fixed)", ["645 train / 120 test ids", "Nothing was trained on either"])
    s.arrow(980, 175, 1080, 175)
    s.box(1080, 60, 770, 110, "Verifier sets 1 to 3 (40 outputs each)", ["Set 1 and 2: Qwen 1.5B, set 3: Qwen 3B. Labeled blind by Claude."])
    s.box(1080, 190, 770, 190, "Final comparison: 120 unseen reports", ["40 held-out test reports + 80 from the train split", "(unused: nothing was ever trained), each with a plain draft", "and a best-of-N pick = 240 outputs, 202 distinct to label"], accent=True)
    s.box(1080, 400, 770, 170, "Labels (AI-assigned)", ["H hedge level changed  |  N number or side wrong", "F unsupported or wrong content  |  O key finding left out"])
    return s


def diagram_errors():
    s = Svg(1900, 520, "Error types used in the labels")
    s.text(40, 54, "The four kinds of error we label (illustrative examples, not quotes from the data)", 28, INK, 600)
    cards = [("H  Certainty changed", ["Report: 'may represent atelectasis'", "Draft: 'this is atelectasis'", "A hedge was dropped or added"]),
             ("N  Number or side wrong", ["Report: 'blunted on the right'", "Draft: 'on the left'", "Also invented numbers or times"]),
             ("F  Unsupported content", ["Report: no recommendation", "Draft: 'no need to worry'", "Also wrong explanations of terms"]),
             ("O  Key finding left out", ["Report impression: 'emphysema'", "Draft never mentions it", "Checked by the omission score"])]
    w, gap, x0, y = 430, 30, 40, 100
    for i, (t, lines) in enumerate(cards):
        s.box(x0 + i * (w + gap), y, w, 190, t, lines)
    s.text(40, 350, "A minor wrong explanation of a term is noted as 'f' and is not counted as an error. Omission is labeled separately from H, N and F.", 17, MUTED)
    s.text(40, 382, "Definitions: results/human_labeling/GUIDELINES.md (the same rules were used for labeling).", 17, MUTED)
    return s


def diagrams():
    from playwright.sync_api import sync_playwright

    d = OUT / "diagrams"
    d.mkdir(parents=True, exist_ok=True)
    made = []
    for name, fn in (("pipeline", diagram_pipeline), ("verifier-components", diagram_verifier),
                     ("data-and-evaluation", diagram_data), ("error-types", diagram_errors)):
        svg = fn()
        (d / f"{name}.svg").write_text(svg.render(), encoding="utf-8")
        made.append((name, svg.w, svg.h))
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        for name, w, h in made:
            page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
            page.goto((d / f"{name}.svg").as_uri())
            page.screenshot(path=str(d / f"{name}.png"))
            page.close()
            print("saved diagrams/" + name, flush=True)
        browser.close()


if __name__ == "__main__":
    diagrams()
    charts()
