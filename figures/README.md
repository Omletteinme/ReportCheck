# Figures for the paper, report and slides

Every image here is generated from the real demo and the real result files, so it can be redone after any change
(commands at the bottom). Use the PNGs in slides and the report; use the PDFs (charts) or SVGs (diagrams) when the
paper needs vector graphics. The SVG diagrams can be edited by hand in any text editor or Inkscape.

## Rules for using these images

1. **Labels are AI-assigned.** Every error rate and AUC here comes from labels assigned blind by Claude (an AI), not by
   humans. Say so in the caption or the text. Do not call them "human evaluation".
2. **Nothing was trained.** The model is pretrained Qwen2.5-1.5B-Instruct and the entailment checker is a pretrained
   DeBERTa NLI model. The page no longer says this, so say it in the slides.
3. **80 of the 120 evaluation reports come from the train split** (never trained on, because nothing was trained).
   40 are the held-out test reports.
4. **Circular rows.** Verifier-scored numbers for the checked draft are circular (the verifier picked the draft).
   Only the labeled rows and the "plain outputs" AUC are independent. `charts/circular-vs-labeled` shows the difference.
5. **The checked drafts are not simpler to read** (`charts/readability`). Do not claim simplification.
6. **Credit the 3D figure** wherever a screenshot of it appears: "BodyParts3D, (c) The Database Center for Life Science,
   licensed under CC Attribution 4.0 International" (it is already printed on the page in the screenshots).
7. **No patient data.** Reports are from the public, anonymised Open-i chest X-ray set (`XXXX` marks text the NLM
   removed). The three synthetic examples in the demo are marked as such on the page.
8. Demo screenshots show pre-computed examples chosen to show different cases, not typical ones.

## demo/ (1440 x 900 page at 2x, light mode)

| File | Shows | Good for |
|---|---|---|
| `01-overview-empty` | The page before anything is loaded | Slide: "the demo" |
| `02-full-ui-example` | Whole first screen with example 1: 3D body map, callouts, report box, output | **Hero slide**, paper Figure 1 |
| `02b-full-page` | The full scrolling page | Report appendix |
| `03-input-panel` | Report card: example chips, text box, upload, Quick check and Best of 8 | Report: how to use it |
| `04-upload-loaded` | After a `.txt` file is uploaded ("Loaded ...") | Report: file upload |
| `05-body-map-callouts` | 3D figure with callout cards and dashed leader lines | Slide: body map |
| `06-body-map-selected` | A region selected: camera zoomed, organ highlighted, statement shown | Slide: body map |
| `07-body-map-whole-body` | Whole-body view | Slide: full skeleton |
| `08-map-patient-version`, `09-map-original-report` | Same map from the patient text and from the original report | Report: two modes |
| `10-output-checked-draft`, `11-output-plain-draft`, `12-output-original` | The three output tabs with flags and score bars | Report: output, slide: what we flag |
| `13-flag-tooltip-*` | A flagged word with the reason bubble (left/right, number, biggest gain) | Slide: "what we caught" |
| `14a-hedge-plain-draft`, `14b-hedge-checked-draft` | Hedge example: plain draft vs checked draft | Slide: hedge errors |
| `15-findings-explorer`, `16-findings-filter-hedged` | Findings explorer, then with the Hedged filter | Report: explorer |
| `17-results-table-120` | The 120-report comparison table as shown on the page | Report: results (see rule 4) |
| `18a-mobile-top`, `18b-mobile-full-page`, `18c-mobile-output` | Phone layout (375 px wide) | Report: responsive layout |

Suggested caption for `02-full-ui-example`: "The demo. The 3D map shows where each statement of the checked patient version
points; flagged words and the findings explorer show what the checker caught."

## diagrams/ (SVG + PNG)

| File | Shows | Good for |
|---|---|---|
| `pipeline` | Report -> parse -> draft -> verify -> pick -> glossary -> show; says "pretrained, not fine-tuned" | Paper method figure, slide |
| `verifier-components` | The five checks with weights, and the hard checks a chosen draft must pass | Paper method, slide |
| `data-and-evaluation` | Open-i reports, the split, verifier sets 1 to 3, the 120-report final run, labels | Paper experiments, slide |
| `error-types` | The four error labels H, N, F, O with illustrative examples (not quotes from the data) | Report: labeling |

## charts/ (PNG 300 dpi + PDF, numbers parsed from `results/`, never typed by hand)

| File | Shows | Data source | Caveat |
|---|---|---|---|
| `error-rates` | Labeled error rates, plain vs best-of-N, with 95% CIs | `results/final_summary.md` | Unsupported content falls (-0.11); hedge and number/side errors do not change meaningfully; omissions rose (+0.06, CI touches 0) |
| `verifier-auc` | AUC (total score vs any labeled error) before and after the new checks, per set | `results/verifier_auc_before.txt`, `verifier_auc_after.txt` | Set 3 (3B outputs) drops to 0.55; most CIs are wide (n = 20 to 60) |
| `auc-plain-outputs` | AUC per verifier component on the 120 plain drafts | `results/final_summary.md` | Not circular. Omission has 5 positive cases: weak evidence |
| `readability` | Reading grade (FK) and simplicity, plain vs checked | `results/final_summary.md` | Checked drafts are not simpler |
| `circular-vs-labeled` | Verifier-scored gain vs labeled gain | `results/final_summary.md` | Grey rows are circular |

AUC: probability that a random clean output gets a higher score than a random flawed one (0.5 = chance, 1 = perfect).

## Regenerate

```bash
pip install -r requirements-figures.txt        # playwright + matplotlib; uses the installed Microsoft Edge
.venv/Scripts/python scripts/make_figures.py   # diagrams and charts, a few seconds
.venv/Scripts/python scripts/capture_screenshots.py          # demo screenshots (starts the demo server itself)
.venv/Scripts/python scripts/capture_screenshots.py --live   # also runs one real Quick check on the GPU (about 30 s)
```

Screenshots use reduced-motion emulation so they are repeatable. `tests/test_figures.py` checks that the result files
still parse and that this index lists exactly the files in these folders.
